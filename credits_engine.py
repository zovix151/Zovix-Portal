"""Credit validation and deduction backed by the shared Supabase PostgreSQL adapter."""

import logging
from datetime import datetime

import streamlit as st

import postgres_db as db

logger = logging.getLogger("Zovix.Credits")


FACE_VIDEO_WORD_PRICES = {
    "Standard": ((50, 15), (85, 20), (120, 30)),
    "HD": ((50, 20), (85, 26), (120, 40)),
    "4K": ((50, 25), (85, 32), (120, 50)),
}


def get_prompt_word_cost(engine_name, quality="Standard", word_count=0):
    """Return the word-band credit cost matching the face-video pricing rules."""
    engine_key = str(engine_name or "").strip().lower()
    face_like_engines = {
        "face video generator",
        "face video studio",
        "expressive face video",
        "ai sales video",
        "sales video",
        "sales prompt",
    }

    if engine_key in face_like_engines:
        try:
            words = int(word_count or 0)
        except (TypeError, ValueError):
            words = 0
        if words <= 0:
            return FACE_VIDEO_WORD_PRICES.get(quality, FACE_VIDEO_WORD_PRICES["Standard"])[0][1]
        for maximum_words, price in FACE_VIDEO_WORD_PRICES.get(quality, FACE_VIDEO_WORD_PRICES["Standard"]):
            if words <= maximum_words:
                return price
        return None

    quality_cost_map = {"Standard": 25, "HD": 60, "4K": 110}
    return quality_cost_map.get(quality, 3)


def get_face_video_token_cost(quality="Standard", word_count=0):
    """Return the face-video price for the script word-count band."""
    return get_prompt_word_cost("Face Video Generator", quality, word_count)


def validate_and_deduct_tokens(engine_name, quality="Standard", word_count=None):
    # Face-video and sales prompt pricing follows the same quality and script word-count table.
    required = get_prompt_word_cost(engine_name, quality, word_count)
    if required is None:
        return False, 0, "Prompt is limited to 120 words. Please shorten it."
    low_balance_threshold = 25
    username = str(st.session_state.get("logged_user") or "").strip()

    if not username:
        return False, required, f"Please login and add credits. Required: {required} credits."

    conn = None
    try:
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT credits, voucher_credits, voucher_expires_at FROM users "
            "WHERE LOWER(TRIM(username)) = LOWER(TRIM(?)) FOR UPDATE",
            (username,),
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return False, required, "Could not read your credit balance. Please log in again."

        standard = int(row[0] or 0)
        voucher = int(row[1] or 0)
        expires_at = row[2]
        if voucher and expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if datetime.now(expires_at.tzinfo) > expires_at if getattr(expires_at, "tzinfo", None) else datetime.now() > expires_at:
                voucher = 0
                cursor.execute(
                    "UPDATE users SET voucher_credits = 0, voucher_expires_at = NULL "
                    "WHERE LOWER(TRIM(username)) = LOWER(TRIM(?))",
                    (username,),
                )

        total = standard + voucher
        if total < required:
            conn.rollback()
            return False, required, f"Insufficient credits. Required: {required}, available: {total}."

        if voucher >= required:
            cursor.execute(
                "UPDATE users SET voucher_credits = voucher_credits - ? "
                "WHERE LOWER(TRIM(username)) = LOWER(TRIM(?))",
                (required, username),
            )
        else:
            cursor.execute(
                "UPDATE users SET voucher_credits = 0, credits = credits - ? "
                "WHERE LOWER(TRIM(username)) = LOWER(TRIM(?))",
                (required - voucher, username),
            )
        if cursor.rowcount != 1:
            conn.rollback()
            return False, required, "Failed to deduct credits. Please try again."
        conn.commit()

        new_total = total - required
        st.session_state["user_credits"] = new_total
        st.session_state["credit_balance"] = new_total
        suffix = " Low balance." if new_total < low_balance_threshold else ""
        return True, required, f"{required} credits deducted for {engine_name}. Balance: {new_total}.{suffix}"
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.exception("Credit validation failed: %s", exc)
        return False, required, "Could not read your credit balance. Please try again."
    finally:
        if conn:
            conn.close()
