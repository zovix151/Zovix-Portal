"""Standalone Streamlit dashboard for the ZOVIX Ghost Engine Layers 1–7."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

import logging
import os
import time
import streamlit as st

from layer6_master_engine import run_zovix_ghost_engine

logging.basicConfig(level=os.getenv("ZOVIX_LOG_LEVEL", "INFO"))
logger = logging.getLogger("Zovix.Layer7")

st.set_page_config(page_title="ZOVIX · Ghost Engine", page_icon="◈", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(ellipse at 15% 0%, #16212e 0, #090d13 44%, #080b10 100%); }
    [data-testid="stHeader"] { background: transparent; }
    .hero { padding: 1.3rem 0 .8rem; }
    .eyebrow { color: #72e5dc; letter-spacing: .22em; font-size: .72rem; font-weight: 700; }
    .hero h1 { color: #eff7fa; font-size: clamp(2rem, 4vw, 3.25rem); margin: .25rem 0; }
    .hero p { color: #91a2b1; max-width: 700px; }
    [data-testid="stMetric"] { background: #111923; border: 1px solid #233542; padding: 1rem; border-radius: 14px; }
    div.stButton > button[kind="primary"] { background: linear-gradient(100deg,#21bdb1,#7189ff); border: 0; color: #071116; font-weight: 800; }
    div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg,#20cdb8,#7189ff); }
    </style>
    <div class="hero">
      <div class="eyebrow">ZOVIX / CREATIVE SYSTEMS / 07</div>
      <h1>Ghost Engine</h1>
      <p>Six coordinated generation layers. One cinematic master, ready to preview and export.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_script, col_controls = st.columns([1.6, 1], gap="large")
with col_script:
    st.subheader("01 · Your scene")
    script = st.text_area(
        "Script or visual prompt",
        height=245,
        placeholder='Describe the scene and include spoken dialogue in quotes, for example: A lone rider crosses a rain-lit city. “We leave at dawn.”',
        help="Layer 1 uses the prompt to direct the scene. Include exact dialogue if you want those words spoken.",
        key="ghost_script",
    )
with col_controls:
    st.subheader("02 · Director controls")
    camera_motion = st.selectbox("Camera motion", ["Dolly Zoom", "Slow Pan", "Crane Shot", "Tracking"], index=1)
    lighting = st.selectbox("Lighting mood", ["Volumetric Golden Hour", "Dramatic Rim Light", "Cyberpunk Neon"], index=0)
    atmosphere = st.selectbox("Atmosphere FX", ["None", "Dust Motes", "Rain", "Fog", "Embers"], index=0)
    emotion = st.selectbox("Emotion state", ["Calm", "Royal", "Sad", "Angry", "Excited"], index=0)
    upscale_scale = st.select_slider("Neural upscale", options=[2, 4], value=4, format_func=lambda value: f"{value}×")

st.markdown("---")
metric_cols = st.columns(3)
metric_cols[0].metric("Estimated cost / scene", f"₹{float(os.getenv('ZOVIX_ESTIMATED_SCENE_COST_INR', '23.00')):.2f}")
metric_cols[1].metric("Pipeline", "6 layers")
metric_cols[2].metric("Export", "MP4 · H.264")
st.caption("Cost is an estimate configured for the ₹20–25 target; actual provider billing can vary. This dashboard does not charge an account.")

run_col, ambience_col = st.columns([1, 2])
with run_col:
    run_clicked = st.button("▶  Generate cinematic master", type="primary", use_container_width=True)
with ambience_col:
    ambience_upload = st.file_uploader("Optional ambient soundscape", type=["mp3", "wav", "m4a", "aac", "ogg"], key="ghost_ambience")

if run_clicked:
    if not script.strip():
        st.warning("Enter a script or scene prompt to begin.")
    else:
        uploaded_ambience_path = None
        if ambience_upload is not None:
            ambience_dir = Path("static/outputs")
            ambience_dir.mkdir(parents=True, exist_ok=True)
            uploaded_ambience_path = ambience_dir / f"dashboard_ambience_{int(time.time())}_{Path(ambience_upload.name).name}"
            uploaded_ambience_path.write_bytes(ambience_upload.getvalue())
        st.subheader("03 · Live pipeline")
        progress = st.progress(0.0, text="Preparing the six generation layers…")
        live_status = st.empty()
        step_list = st.empty()
        completed_steps: set[int] = set()
        current_step = {"index": 0}
        started = time.perf_counter()

        def on_progress(event: dict) -> None:
            step_index = int(event["step"])
            if event["state"] == "complete":
                completed_steps.add(step_index)
            current_step["index"] = step_index
            progress.progress(float(event["progress"]), text=f"{event['stage']} · {event['state']}")
            live_status.caption(f"Step {step_index}/6 · {event['stage']} · {event['elapsed_seconds']:.0f}s elapsed")
            rows = []
            names = [
                "Spatial Director", "Flux Keyframe + Depth", "Camera Motion",
                "Atmosphere + Lighting", "Dialogue + Lip Sync", "Upscale + Audio Master",
            ]
            for number, name in enumerate(names, start=1):
                marker = "✓" if number in completed_steps else ("◌" if number == current_step["index"] else "·")
                rows.append(f"{marker}  Layer {number} — {name}")
            step_list.markdown("  \n".join(rows))

        try:
            output_path = run_zovix_ghost_engine(
                script,
                config_overrides={
                    "camera_motion": camera_motion,
                    "lighting_setup": lighting,
                    "atmosphere_fx": atmosphere,
                    "emotion_state": emotion,
                },
                progress_callback=on_progress,
                ambience_path=str(uploaded_ambience_path) if uploaded_ambience_path else None,
                upscale_scale=upscale_scale,
            )
            elapsed = time.perf_counter() - started
            st.session_state["ghost_engine_last_output"] = output_path
            st.session_state["ghost_engine_last_runtime"] = elapsed
            progress.progress(1.0, text="Master render complete")
            live_status.success(f"Completed in {elapsed:.1f} seconds · estimated scene cost ₹{float(os.getenv('ZOVIX_ESTIMATED_SCENE_COST_INR', '23.00')):.2f}")
            logger.info("Dashboard render complete in %.2fs: %s", elapsed, output_path)
            st.rerun()
        except Exception as exc:
            logger.exception("Dashboard Ghost Engine render failed.")
            live_status.error(str(exc))
        finally:
            if uploaded_ambience_path:
                uploaded_ambience_path.unlink(missing_ok=True)

last_output = st.session_state.get("ghost_engine_last_output")
if last_output and Path(last_output).is_file():
    st.markdown("---")
    st.subheader("04 · Master preview")
    final_col, details_col = st.columns([1.5, 1], gap="large")
    with final_col:
        st.video(last_output)
    with details_col:
        st.metric("Render time", f"{st.session_state.get('ghost_engine_last_runtime', 0):.1f}s")
        st.metric("Scene estimate", f"₹{float(os.getenv('ZOVIX_ESTIMATED_SCENE_COST_INR', '23.00')):.2f}")
        with open(last_output, "rb") as video_file:
            st.download_button(
                "⬇  Download Zovix Cinematic Video", data=video_file,
                file_name="zovix_cinematic_video.mp4",
                mime="video/mp4", use_container_width=True,
            )
