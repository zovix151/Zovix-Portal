"""Cinematic Studio page backed by the Ghost Engine pipeline."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

import logging

import streamlit as st

from layer6_master_engine import GHOST_QUALITY_PROFILES, run_zovix_ghost_engine
from spatial_director_engine import (
    _ATMOSPHERE_EFFECTS,
    _CAMERA_MOTIONS,
    _CHARACTER_ACTION_OPTIONS,
    _LIGHTING_SETUPS,
    get_openai_api_key,
)

logger = logging.getLogger("Zovix.Layer7")


def render_ghost_engine_studio(
    save_output_callback=None,
    load_portfolio_callback=None,
    deduct_tokens_callback=None,
    refund_tokens_callback=None,
) -> None:
    """Render scene controls, pipeline progress, and the last master render."""
    brand_column, back_column = st.columns([0.74, 0.26], vertical_alignment="center")
    with brand_column:
        st.markdown(
            """
            <div class="ghost-engine-brand" aria-label="Zovix AI Studio">
              <span class="ghost-engine-brand-mark">Z</span>
              <span class="ghost-engine-brand-copy"><b>ZOVIX</b><small>AI STUDIO</small></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with back_column:
        if st.button(
            "← Back to Studio",
            key="ghost_engine_back_to_studio",
            type="secondary",
            width="content",
        ):
            st.session_state["current_page"] = "studio"
            st.query_params["page"] = "studio"
            st.rerun()

    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.st-key-ghost_engine_back_to_studio) > div[data-testid="stMainBlockContainer"],
        section[data-testid="stMain"]:has(.st-key-ghost_engine_back_to_studio) .block-container {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        .ghost-engine-brand { display:flex; align-items:center; gap:9px; min-height:42px; color:#163c68; font-family:'Inter',Arial,sans-serif; }
        .ghost-engine-brand-mark { display:flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg,#16c6dc,#6959ed); color:#fff; font-size:24px; font-weight:850; box-shadow:0 4px 12px rgba(58,102,206,.2); }
        .ghost-engine-brand-copy { display:flex; flex-direction:column; line-height:1; letter-spacing:.5px; }
        .ghost-engine-brand-copy b { font-size:18px; font-weight:850; }
        .ghost-engine-brand-copy small { margin-top:4px; color:#74869a; font-size:8px; font-weight:750; letter-spacing:2px; }
        .ghost-engine-hero {
            position: relative;
            isolation: isolate;
            transform: none;
            transform-style: flat;
            display: flex;
            box-sizing: border-box;
            width: 100%;
            max-width: 100%;
            min-width: 0;
            min-height: 234px;
            flex-direction: column;
            align-items: flex-start;
            justify-content: center;
            gap: 8px;
            overflow: hidden;
            margin-bottom: 18px;
            padding: 34px clamp(22px, 4vw, 54px);
            background:
                linear-gradient(90deg, rgba(12,43,83,.88) 0%, rgba(12,43,83,.7) 30%, rgba(12,43,83,.12) 72%, rgba(12,43,83,.02)),
                url('/app/static/studio_cinematic_engine.webp') center 43% / cover no-repeat;
            border: 1px solid rgba(255,255,255,.48);
            border-radius: 14px;
            box-shadow: 0 12px 30px rgba(32,77,126,.12);
            text-align: left;
        }
        section[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.st-key-ghost_engine_back_to_studio) {
            position: relative !important;
            z-index: 30 !important;
            height: auto !important;
            margin: 2px 0 14px !important;
            overflow: visible !important;
            pointer-events: auto !important;
        }
        section[data-testid="stMain"]:has(.st-key-ghost_engine_back_to_studio)
        [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:has(.st-key-ghost_engine_back_to_studio) {
            margin-bottom: -22px !important;
        }
        section[data-testid="stMain"] [data-testid="stColumn"]:has(.st-key-ghost_engine_back_to_studio) {
            position: relative !important;
            top: auto !important;
            right: auto !important;
            flex: 1 1 auto !important;
            width: auto !important;
            min-width: 0 !important;
            pointer-events: auto !important;
        }
        section[data-testid="stMain"] [class*="st-key-ghost_engine_back_to_studio"] {
            width: fit-content !important;
            margin: 0 0 0 auto !important;
        }
        .ghost-engine-hero::before {
            position: absolute;
            z-index: 0;
            inset: 0;
            content: "";
            background:
                radial-gradient(ellipse at 50% 8%, rgba(255,255,255,.2), transparent 66%),
                linear-gradient(180deg, rgba(255,255,255,.12), transparent 55%);
            pointer-events: none;
        }
        .ghost-engine-hero::after {
            position: absolute;
            z-index: 0;
            inset: 0;
            content: "";
            border: 1px solid rgba(255,255,255,.16);
            border-radius: inherit;
            background: linear-gradient(
                90deg,
                rgba(2,8,20,.4) 0%,
                rgba(255,255,255,.035) 12%,
                transparent 35%,
                transparent 65%,
                rgba(255,255,255,.035) 88%,
                rgba(2,8,20,.4) 100%
            );
            box-shadow: inset 0 0 42px rgba(2,8,20,.2);
            pointer-events: none;
        }
        .ghost-engine-hero > * {
            position: relative;
            z-index: 1;
            box-sizing: border-box;
            max-width: 100%;
            min-width: 0;
        }
        .ghost-engine-hero .ghost-engine-badge {
            color: #56e4f3;
            font-family: 'Inter', Arial, sans-serif !important;
            font-size: 11px !important;
            font-weight: 800 !important;
            line-height: 1.4 !important;
            letter-spacing: 1.5px;
            text-shadow: 0 2px 16px rgba(0,0,0,.8);
            overflow-wrap: anywhere;
        }
        .ghost-engine-hero h1 {
            width: auto;
            max-width: 100%;
            margin: 3px 0;
            color: #ffffff;
            font-family: 'Inter', Arial, sans-serif !important;
            font-size: clamp(30px, 3.5vw, 38px) !important;
            font-weight: 800 !important;
            line-height: 1.2 !important;
            letter-spacing: -0.02em !important;
            overflow-wrap: anywhere;
            text-wrap: balance;
        }
        .ghost-engine-hero h1 span { font: inherit; color: #31c6e7; }
        .ghost-engine-hero p {
            width: min(100%, 540px);
            max-width: 100%;
            margin: 0;
            color: rgba(255,255,255,.96);
            font-family: 'Inter', Arial, sans-serif !important;
            font-size: clamp(14px, 1.5vw, 16px) !important;
            font-weight: 600 !important;
            line-height: 1.5 !important;
            letter-spacing: 0 !important;
            overflow-wrap: break-word;
            text-wrap: pretty;
        }
        .ghost-engine-output-title,
        .ghost-engine-section-title {
            margin: 0 0 14px;
            color: #173b66;
            font: 750 16px/1.3 'Inter', sans-serif;
        }
        section[data-testid="stMain"] .ghost-engine-hero h1 span,
        section[data-testid="stMain"] .ghost-engine-hero p {
            color: #ffffff !important;
            text-shadow: 0 2px 18px rgba(0,0,0,.62);
        }
        section[data-testid="stMain"] .ghost-engine-hero h1 {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        section[data-testid="stMain"] .ghost-engine-hero h1 span { color: #31c6e7 !important; -webkit-text-fill-color: #31c6e7 !important; }
        [data-testid="stMetric"] {
            height: 100%;
            padding: 14px 16px;
            border: 1px solid #dce7e4 !important;
            border-radius: 12px;
            background: #ffffff !important;
            box-shadow: 0 4px 14px rgba(26,55,56,.05);
        }
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            color: #263638 !important;
            background: #f3f8fd !important;
            background-image: none !important;
        }
        section[data-testid="stMain"] .block-container {
            box-sizing: border-box !important;
            width: 100% !important;
            max-width: 1520px !important;
            margin: 0 auto !important;
            padding: 0 clamp(32px, 4vw, 56px) 30px !important;
            color: #263638 !important;
        }
        section[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorder"] {
            color: #263638 !important;
            background: #ffffff !important;
            border-color: #e1eaf3 !important;
            border-radius: 14px !important;
            box-shadow: 0 5px 18px rgba(43,81,118,.065) !important;
        }
        section[data-testid="stMain"] h1,
        section[data-testid="stMain"] h2,
        section[data-testid="stMain"] h3,
        section[data-testid="stMain"] h4,
        section[data-testid="stMain"] p,
        section[data-testid="stMain"] label,
        section[data-testid="stMain"] [data-testid="stMarkdownContainer"],
        section[data-testid="stMain"] [data-testid="stCaptionContainer"],
        section[data-testid="stMain"] [data-testid="stWidgetLabel"] {
            color: #263638 !important;
            -webkit-text-fill-color: #263638 !important;
        }
        section[data-testid="stMain"] input,
        section[data-testid="stMain"] textarea,
        section[data-testid="stMain"] [data-baseweb="select"] > div {
            color: #263638 !important;
            -webkit-text-fill-color: #263638 !important;
            background: #ffffff !important;
            border-color: #cbd8d5 !important;
        }
        section[data-testid="stMain"] [data-testid="stFileUploader"],
        section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] {
            color: #263638 !important;
            background: #ffffff !important;
            border-color: #cbd8d5 !important;
        }
        section[data-testid="stMain"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stMain"] [data-testid="stCaptionContainer"] p {
            color: #66809a !important;
            font-family: 'Inter', Arial, sans-serif !important;
        }
        section[data-testid="stMain"] [data-testid="stTextArea"] textarea {
            min-height: 112px !important;
            border-radius: 9px !important;
            border-color: #d9e5f1 !important;
            font: 13px/1.5 'Inter', Arial, sans-serif !important;
        }
        section[data-testid="stMain"] [data-baseweb="select"] > div {
            min-height: 40px !important;
            border-radius: 9px !important;
        }
        section[data-testid="stMain"] input[type="checkbox"] { accent-color: #387ee8 !important; }
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button,
        section[data-testid="stMain"] [data-testid="stLinkButton"] a {
            color: #2875bc !important;
            background: #f5faff !important;
            border: 1px solid #dce8f4 !important;
            border-radius: 9px !important;
            font: 650 12px 'Inter',Arial,sans-serif !important;
            text-decoration: none !important;
        }
        section[data-testid="stMain"] [data-testid="stMetricLabel"],
        section[data-testid="stMain"] [data-testid="stMetricValue"],
        section[data-testid="stMain"] [data-testid="stMetricDelta"] {
            color: #203638 !important;
            -webkit-text-fill-color: #203638 !important;
        }
        section[data-testid="stMain"] [data-testid="stProgress"] > div {
            background: #e2ecea !important;
        }
        section[data-testid="stMain"] [data-testid="stProgress"] > div > div {
            background: linear-gradient(90deg, #16a6a0, #6b70dc) !important;
        }
        section[data-testid="stMain"] .st-key-ghost_generate_master button {
            color: #ffffff !important;
            min-height: 42px !important;
            background: linear-gradient(105deg, #08b7d4, #5960e8) !important;
            border-color: transparent !important;
            border-radius: 9px !important;
            font: 700 13px 'Inter', Arial, sans-serif !important;
        }
        section[data-testid="stMain"] .st-key-ghost_engine_back_to_studio button {
            min-height: 36px !important;
            color: #2875bc !important;
            background: rgba(255,255,255,.94) !important;
            border: 1px solid #dce8f4 !important;
            border-radius: 22px !important;
            font: 650 12px 'Inter', Arial, sans-serif !important;
            box-shadow: 0 2px 8px rgba(49,99,151,.08) !important;
        }
        section[data-testid="stMain"] [class*="st-key-ghost_engine_gallery_card_"] [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 10px !important;
            border-radius: 12px !important;
        }
        section[data-testid="stMain"] [class*="st-key-ghost_engine_gallery_card_"] video {
            width: 100% !important;
            aspect-ratio: 16 / 9 !important;
            object-fit: cover !important;
            border-radius: 9px !important;
        }
        .ghost-engine-gallery-title { color:#173b66; font:750 16px/1.3 'Inter',Arial,sans-serif; }
        .ghost-engine-gallery-subtitle { color:#71849a; font:400 12px/1.5 'Inter',Arial,sans-serif; }
        @media (max-width: 768px) {
            section[data-testid="stMain"] .block-container {
                max-width: 100% !important;
                padding: 0 22px 22px !important;
            }
            section[data-testid="stMain"]:has(.st-key-ghost_engine_back_to_studio)
            [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:has(.st-key-ghost_engine_back_to_studio) {
                margin-bottom: -18px !important;
            }
            .ghost-engine-hero {
                min-height: 220px;
                padding: 24px 18px;
                border-radius: 12px;
                transform: none;
            }
            .ghost-engine-hero .ghost-engine-badge {
                font-size: 10px !important;
                letter-spacing: 1px;
            }
            .ghost-engine-hero h1 {
                font-size: clamp(26px, 8vw, 34px) !important;
            }
            .ghost-engine-hero p {
                width: 100%;
            }
            section[data-testid="stMain"] [data-testid="stColumn"]:has(.st-key-ghost_engine_back_to_studio) { width: auto !important; min-width: 0 !important; }
            section[data-testid="stMain"] .st-key-ghost_engine_back_to_studio button { padding: 7px 10px !important; font-size: 11px !important; white-space: nowrap !important; }
            .ghost-engine-brand-copy b { font-size: 16px; }
        }
        @media (min-width: 769px) and (max-width: 1100px) {
            .ghost-engine-hero { min-height: 234px; }
        }
        @media (max-width: 640px) {
            section[data-testid="stMain"] .block-container {
                padding: 0 22px 22px !important;
            }
            section[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.st-key-ghost_script) > [data-testid="column"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 0 !important;
            }
            section[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
            }
            section[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 0 !important;
            }
            section[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.st-key-ghost_engine_back_to_studio) > [data-testid="column"]:first-child {
                flex: 0 0 65% !important;
                width: 65% !important;
            }
            section[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.st-key-ghost_engine_back_to_studio) > [data-testid="column"]:last-child {
                flex: 0 0 35% !important;
                width: 35% !important;
            }
            section[data-testid="stMain"] [data-testid="stMainBlockContainer"] {
                padding-left: 0 !important;
                padding-right: 0 !important;
            }
        }
        @media (max-width: 480px) {
            section[data-testid="stMain"] .block-container {
                padding: 0 18px 22px !important;
            }
        }
        </style>
        <section class="ghost-engine-hero">
          <span class="ghost-engine-badge">ZOVIX AI CINEMATIC GENERATION</span>
          <h1>Cinematic <span>Studio</span></h1>
          <p>Direct your scene. Create a cinematic story.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    config_column, output_column = st.columns([1, 1.2], gap="medium")
    with config_column:
        with st.container(border=True):
            st.markdown(
                "<h3 class='ghost-engine-section-title'>Scene &amp; Director Controls</h3>",
                unsafe_allow_html=True,
            )
            script = st.text_area(
                "Scene script / prompt",
                height=112,
                max_chars=2000,
                placeholder="Write your scene and character direction...",
                help="GPT-4o optimizes the scene prompt; Flux creates the keyframe and Wan animates it.",
                key="ghost_script",
            )
            st.markdown(
                "<p style='font:700 11px Inter,Arial,sans-serif;color:#64748b;margin:8px 0 2px'>"
                "DIRECTOR CONTROLS</p>",
                unsafe_allow_html=True,
            )
            camera_column, lighting_column = st.columns(2, gap="medium")
            with camera_column:
                camera_motion = st.selectbox(
                    "Camera Motion",
                    list(_CAMERA_MOTIONS),
                    index=_CAMERA_MOTIONS.index("Orbit Left (360)"),
                    key="ghost_camera_motion",
                    help="Choose the camera path for your scene.",
                )
                st.caption("Choose camera movement for your scene.")
            with lighting_column:
                lighting_setup = st.selectbox(
                    "Lighting",
                    list(_LIGHTING_SETUPS),
                    index=0,
                    key="ghost_lighting_setup",
                )
                st.caption("Set the mood with cinematic lighting.")

            atmosphere_column, action_column = st.columns(2, gap="medium")
            with atmosphere_column:
                atmosphere_fx = st.selectbox(
                    "Atmosphere",
                    list(_ATMOSPHERE_EFFECTS),
                    index=4,
                    key="ghost_atmosphere_fx",
                )
                st.caption("Add atmosphere and environmental effects.")
            with action_column:
                character_action = st.selectbox(
                    "Character Action",
                    list(_CHARACTER_ACTION_OPTIONS),
                    index=0,
                    key="ghost_character_action",
                    help=(
                        "Expressive dialogue, facial expressions and shouting use LivePortrait refinement. "
                        "Other actions use the fast image-to-video route."
                    ),
                )
                st.caption("Define what the character will do.")
            if character_action != "None (Camera Motion Only)":
                st.caption(
                    "The selected action is sent directly to the hosted image-to-video model with the Flux keyframe. "
                    "Hosted model usage may be billed."
                )
            if st.session_state.get("ghost_video_quality") not in GHOST_QUALITY_PROFILES:
                st.session_state["ghost_video_quality"] = "Standard"
            quality_column, face_lock_column = st.columns(2, gap="medium")
            with quality_column:
                quality = st.selectbox(
                    "Video Quality",
                    list(GHOST_QUALITY_PROFILES),
                    index=0,
                    key="ghost_video_quality",
                    help="Standard: 720p/30. HD: 1080p/30 with 2x enhancement.",
                )
                st.caption("Select the output quality for your video.")
            with face_lock_column:
                face_lock = st.checkbox(
                    "Enable Face Lock",
                    key="ghost_face_lock_enabled",
                    help="Use a reference face to guide the generated character's facial identity.",
                )
                st.caption("Keep the character's face consistent.")
                face_reference = None
                if face_lock:
                    face_reference = st.file_uploader(
                        "Face reference image",
                        type=["png", "jpg", "jpeg", "webp"],
                        key="ghost_face_reference",
                        help="Upload a clear, front-facing image. It guides the Flux keyframe and may incur model usage charges.",
                    )
            quality_descriptions = {
                "Standard": "720p · 30 FPS · fast render",
                "HD": "1080p · 30 FPS · 2x enhancement · higher detail",
            }
            st.caption(quality_descriptions[quality])
            run_clicked = st.button(
                "▶ Generate Story Video",
                key="ghost_generate_master",
                type="primary",
                width="stretch",
            )

    with output_column:
        with st.container(border=True):
            st.markdown(
                "<h3 class='ghost-engine-output-title'>Final Cinematic Video</h3>",
                unsafe_allow_html=True,
            )

            if run_clicked:
                if not script.strip():
                    st.warning("Enter a script or scene prompt to begin.")
                elif face_lock and face_reference is None:
                    st.warning("Upload a face reference image to use Face Lock.")
                elif not get_openai_api_key():
                    st.error(
                        "OPENAI_API_KEY is not loaded. Add it to the project .env file or Streamlit secrets."
                    )
                elif not deduct_tokens_callback:
                    st.error("Token billing is unavailable. Please try again later.")
                else:
                    deducted_tokens = 0
                    billing_message = "Token validation failed. Please try again."
                    try:
                        billing_ok, deducted_tokens, billing_message = deduct_tokens_callback(
                            "Cinematic Engine",
                            quality=quality,
                        )
                    except Exception as exc:
                        logger.exception("Cinematic Engine token validation failed.")
                        billing_ok = False

                    if not billing_ok:
                        st.error(billing_message)
                    else:
                        generation_succeeded = False
                        try:
                            with st.spinner("Creating your cinematic video…"):
                                output_path = run_zovix_ghost_engine(
                                    script,
                                    config_overrides={
                                        "camera_motion": camera_motion,
                                        "lighting_setup": lighting_setup,
                                        "atmosphere_fx": atmosphere_fx,
                                        "character_action": character_action,
                                    },
                                    face_reference_bytes=(
                                        face_reference.getvalue()
                                        if face_lock and face_reference
                                        else None
                                    ),
                                    quality=quality,
                                )
                                generation_succeeded = True
                                st.session_state["ghost_engine_last_output"] = output_path
                                st.session_state["ghost_engine_last_quality"] = quality
                            output_name = f"cinematic_{Path(output_path).name}"
                            username = st.session_state.get("logged_user", "")
                            if username and save_output_callback:
                                save_output_callback(
                                    username,
                                    output_name,
                                    script.strip(),
                                    output_path,
                                    "Cinematic Engine",
                                )
                                if load_portfolio_callback:
                                    st.session_state["history_renders"] = load_portfolio_callback(username)
                            else:
                                history = st.session_state.setdefault("history_renders", [])
                                history.insert(0, {
                                    "file_name": output_name,
                                    "prompt": script.strip(),
                                    "path": output_path,
                                    "generation_type": "Cinematic Engine",
                                })
                            logger.info("Cinematic Engine render complete: %s", output_path)
                            st.rerun()
                        except Exception as exc:
                            logger.exception("Cinematic Engine render failed.")
                            if (
                                not generation_succeeded
                                and deducted_tokens > 0
                                and refund_tokens_callback
                            ):
                                refund_tokens_callback(
                                    deducted_tokens,
                                    f"Cinematic Engine generation failed: {exc}",
                                )
                            st.error(f"Video generation failed: {exc}")

            last_output = st.session_state.get("ghost_engine_last_output")
            if last_output and Path(last_output).is_file():
                try:
                    video_bytes = Path(last_output).read_bytes()
                except OSError as exc:
                    logger.exception("Could not read the Cinematic Engine master video.")
                    st.error(f"The generated video could not be opened: {exc}")
                else:
                    st.video(video_bytes, format="video/mp4")
                    output_quality = st.session_state.get("ghost_engine_last_quality", quality)
                    profile = GHOST_QUALITY_PROFILES.get(output_quality, GHOST_QUALITY_PROFILES[quality])
                    st.markdown(
                        "<div style='display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 16px'>"
                        f"<span style='padding:8px 14px;border-radius:22px;background:#e7f7ff;color:#247ab4;font:650 12px Inter,Arial,sans-serif'>{profile['size'][0]}p</span>"
                        f"<span style='padding:8px 14px;border-radius:22px;background:#eef4ff;color:#526bc1;font:650 12px Inter,Arial,sans-serif'>{profile['fps']} FPS</span>"
                        f"<span style='padding:8px 14px;border-radius:22px;background:#e7f7ff;color:#247ab4;font:650 12px Inter,Arial,sans-serif'>{output_quality}</span>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    st.download_button(
                        "Download Zovix Cinematic Video",
                        data=video_bytes,
                        file_name="Zovix Cinematic Video.mp4",
                        mime="video/mp4",
                        width="stretch",
                    )
            # Keep the preview empty until the generated master video is ready.

    st.markdown("---")
    gallery_title_column, gallery_link_column = st.columns([1, 0.2], vertical_alignment="center")
    with gallery_title_column:
        st.markdown("<div class='ghost-engine-gallery-title'>Cinematic Gallery</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='ghost-engine-gallery-subtitle'>Your finished cinematic videos appear here and in My Portfolio.</div>",
            unsafe_allow_html=True,
        )
    with gallery_link_column:
        st.link_button("View All →", "?page=portfolio", width="stretch")
    gallery_items = [
        item for item in st.session_state.get("history_renders", [])
        if item.get("generation_type") == "Cinematic Engine"
        and "cinematic" in str(item.get("file_name", "")).lower()
        and Path(str(item.get("path", ""))).is_file()
    ]
    if not gallery_items:
        st.caption("Your finished cinematic videos will appear here and in My Portfolio.")
    else:
        gallery_columns = st.columns(3, gap="medium")
        for index, (column, item) in enumerate(zip(gallery_columns, gallery_items[:3])):
            with column:
                with st.container(border=True, key=f"ghost_engine_gallery_card_{index}"):
                    st.video(item["path"])
                    st.markdown(f"**{item.get('file_name', 'Cinematic video')}**")
                    prompt = str(item.get("prompt", "Cinematic video")).strip()
                    st.caption(prompt[:100] + ("…" if len(prompt) > 100 else ""))
                    st.caption("🎬 Cinematic · Zovix AI Studio")

    st.markdown(
        """
        <div role="contentinfo" style="text-align:center;padding:18px 12px 24px;color:#64748b;font-family:Inter,Arial,sans-serif;font-size:12px">
          <p style="margin:0 0 8px">© 2026 ZOVIX. All rights reserved.</p>
          <nav style="display:flex;justify-content:center;flex-wrap:wrap;gap:16px">
            <a href="#" style="color:#64748b;text-decoration:none">Privacy Policy</a>
            <a href="#" style="color:#64748b;text-decoration:none">Terms</a>
            <a href="#" style="color:#64748b;text-decoration:none">Support</a>
          </nav>
        </div>
        """,
        unsafe_allow_html=True,
    )
