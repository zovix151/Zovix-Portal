"""Integrated Zovix Ghost Engine workspace page."""

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
    _, back_column = st.columns([0.82, 0.18], vertical_alignment="center")
    with back_column:
        if st.button(
            "← Back to Studio",
            key="ghost_engine_back_to_studio",
            type="secondary",
            use_container_width=True,
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
        section[data-testid="stMain"]:has(.st-key-ghost_engine_back_to_studio)
        [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:has(.st-key-ghost_engine_back_to_studio) {
            margin-bottom: -22px !important;
        }
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
            min-height: 260px;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            overflow: hidden;
            margin-bottom: 18px;
            padding: 36px clamp(20px, 5vw, 64px);
            background:
                linear-gradient(90deg, rgba(5,12,27,.76), rgba(5,12,27,.22) 58%, rgba(5,12,27,.08)),
                url('/app/static/ghost_engine_cityscape.png') center 43% / cover no-repeat;
            border: 1px solid rgba(255,255,255,.18);
            border-radius: 30px;
            box-shadow:
                0 22px 54px rgba(4,12,28,.3),
                inset 24px 0 34px -28px rgba(0,0,0,.82),
                inset -24px 0 34px -28px rgba(0,0,0,.82);
            text-align: center;
        }
        section[data-testid="stMain"] [data-testid="stHorizontalBlock"]:has(.st-key-ghost_engine_back_to_studio) {
            position: relative !important;
            z-index: 30 !important;
            height: 0 !important;
            margin: 0 !important;
            overflow: visible !important;
            pointer-events: none !important;
        }
        section[data-testid="stMain"] [data-testid="stColumn"]:has(.st-key-ghost_engine_back_to_studio) {
            position: absolute !important;
            top: 30px !important;
            right: 18px !important;
            flex: none !important;
            width: 190px !important;
            min-width: 0 !important;
            pointer-events: auto !important;
        }
        section[data-testid="stMain"] [class*="st-key-ghost_engine_back_to_studio"] {
            width: 100% !important;
            margin: 0 !important;
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
            color: #9af7ff;
            font-family: 'Inter', Arial, sans-serif !important;
            font-size: 11px !important;
            font-weight: 800 !important;
            line-height: 1.4 !important;
            letter-spacing: 1.5px;
            text-shadow: 0 2px 16px rgba(0,0,0,.8);
            overflow-wrap: anywhere;
        }
        .ghost-engine-hero h1 {
            width: 100%;
            max-width: 100%;
            margin: 3px 0;
            color: #ffffff;
            font-family: 'Inter', Arial, sans-serif !important;
            font-size: clamp(26px, 4vw, 38px) !important;
            font-weight: 800 !important;
            line-height: 1.2 !important;
            letter-spacing: -0.02em !important;
            overflow-wrap: anywhere;
            text-wrap: balance;
        }
        .ghost-engine-hero h1 span {
            font: inherit;
            background: linear-gradient(135deg, #8cf5ff, #ff9bd7);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .ghost-engine-hero p {
            width: min(100%, 760px);
            max-width: 100%;
            margin: 0;
            color: rgba(255,255,255,.9);
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
            color: #173b3e;
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
        section[data-testid="stMain"] .ghost-engine-hero h1 span {
            background: linear-gradient(135deg, #8cf5ff, #ff9bd7);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent !important;
        }
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
            background: #f3f6f6 !important;
            background-image: none !important;
        }
        section[data-testid="stMain"] .block-container {
            color: #263638 !important;
        }
        section[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorder"] {
            color: #263638 !important;
            background: #ffffff !important;
            border-color: #d2dddb !important;
            box-shadow: 0 6px 18px rgba(26,55,56,.075) !important;
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
            background: linear-gradient(110deg, #138f8b, #5868d9) !important;
            border-color: transparent !important;
        }
        @media (max-width: 768px) {
            .ghost-engine-hero {
                min-height: 220px;
                padding: 30px 18px;
                border-radius: 24px;
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
            section[data-testid="stMain"] [data-testid="stColumn"]:has(.st-key-ghost_engine_back_to_studio) {
                top: 26px !important;
                right: 10px !important;
                width: 160px !important;
            }
            section[data-testid="stMain"]:has(.st-key-ghost_engine_back_to_studio)
            [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:has(.st-key-ghost_engine_back_to_studio) {
                margin-bottom: -18px !important;
            }
        }
        </style>
        <section class="ghost-engine-hero">
          <span class="ghost-engine-badge">ZOVIX · AI CINEMATIC GENERATION</span>
          <h1>Cinematic</h1>
          <p>Direct your scene and create a finished cinematic video, ready to preview and download.</p>
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
                height=180,
                placeholder="Write your scene and character direction.",
                help="GPT-4o optimizes the scene prompt; Flux creates the keyframe and Wan animates it.",
                key="ghost_script",
            )
            st.markdown(
                "<p style='font:700 11px Inter,Arial,sans-serif;color:#64748b;margin:8px 0 2px'>"
                "DIRECTOR CONTROLS</p>",
                unsafe_allow_html=True,
            )
            camera_motion = st.selectbox(
                "Camera motion",
                list(_CAMERA_MOTIONS),
                index=_CAMERA_MOTIONS.index("Orbit Left (360)"),
                key="ghost_camera_motion",
            )
            lighting_setup = st.selectbox(
                "Lighting",
                list(_LIGHTING_SETUPS),
                index=0,
                key="ghost_lighting_setup",
            )
            atmosphere_fx = st.selectbox(
                "Atmosphere",
                list(_ATMOSPHERE_EFFECTS),
                index=4,
                key="ghost_atmosphere_fx",
            )
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
            if character_action != "None (Camera Motion Only)":
                st.caption(
                    "The selected action is sent directly to the hosted image-to-video model with the Flux keyframe. "
                    "Hosted model usage may be billed."
                )
            if st.session_state.get("ghost_video_quality") not in GHOST_QUALITY_PROFILES:
                st.session_state["ghost_video_quality"] = "Standard"
            quality = st.selectbox(
                "Video Quality",
                list(GHOST_QUALITY_PROFILES),
                index=0,
                key="ghost_video_quality",
                help="Standard: 720p/30. HD: 1080p/48 with 2x enhancement.",
            )
            quality_descriptions = {
                "Standard": "720p · 30 FPS · fast render",
                "HD": "1080p · 48 FPS · 2x enhancement · higher detail",
            }
            st.caption(quality_descriptions[quality])
            run_clicked = st.button(
                "▶ GENERATE STORY VIDEO",
                key="ghost_generate_master",
                type="primary",
                use_container_width=True,
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
                            "Ghost Engine",
                            quality=quality,
                        )
                    except Exception as exc:
                        logger.exception("Ghost Engine token validation failed.")
                        billing_ok = False

                    if not billing_ok:
                        st.error(billing_message)
                    else:
                        generation_succeeded = False
                        try:
                            with st.spinner("Generate Zovix Video"):
                                output_path = run_zovix_ghost_engine(
                                    script,
                                    config_overrides={
                                        "camera_motion": camera_motion,
                                        "lighting_setup": lighting_setup,
                                        "atmosphere_fx": atmosphere_fx,
                                        "character_action": character_action,
                                    },
                                    quality=quality,
                                )
                                generation_succeeded = True
                                st.session_state["ghost_engine_last_output"] = output_path
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
                            logger.info("Ghost Engine render complete: %s", output_path)
                            st.rerun()
                        except Exception as exc:
                            logger.exception("Ghost Engine render failed.")
                            if (
                                not generation_succeeded
                                and deducted_tokens > 0
                                and refund_tokens_callback
                            ):
                                refund_tokens_callback(
                                    deducted_tokens,
                                    f"Ghost Engine generation failed: {exc}",
                                )
                            st.error(f"Video generation failed: {exc}")

            last_output = st.session_state.get("ghost_engine_last_output")
            if last_output and Path(last_output).is_file():
                try:
                    video_bytes = Path(last_output).read_bytes()
                except OSError as exc:
                    logger.exception("Could not read the Ghost Engine master video.")
                    st.error(f"The generated video could not be opened: {exc}")
                else:
                    st.video(video_bytes, format="video/mp4")
                    st.download_button(
                        "Download Zovix Cinematic Video",
                        data=video_bytes,
                        file_name="zovix_cinematic_video.mp4",
                        mime="video/mp4",
                        use_container_width=True,
                    )

    st.markdown("---")
    st.markdown("### Cinematic Gallery")
    gallery_items = [
        item for item in st.session_state.get("history_renders", [])
        if item.get("generation_type") == "Cinematic Engine"
        and "cinematic" in str(item.get("file_name", "")).lower()
        and Path(str(item.get("path", ""))).is_file()
    ]
    if not gallery_items:
        st.caption("Your finished cinematic videos will appear here and in My Portfolio.")
    else:
        for start in range(0, min(len(gallery_items), 12), 3):
            gallery_columns = st.columns(3, gap="medium")
            for column, item in zip(gallery_columns, gallery_items[start:start + 3]):
                with column:
                    st.video(item["path"])
                    st.caption(item.get("prompt", "Cinematic video"))

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
