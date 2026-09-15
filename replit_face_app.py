"""Small Replit testing UI for the ZOVIX face-generation endpoint.

Replit hosts the upload/testing UI. GPU inference remains on the configured
RunPod serverless endpoint.
"""

import base64
import os
import time
from typing import Any, Dict

import requests
import streamlit as st


RUNPOD_API_URL = os.getenv("RUNPOD_API_URL", "https://api.runpod.ai/v2").rstrip("/")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "").strip()
RUNPOD_ENDPOINT_FACE = (
    os.getenv("RUNPOD_ENDPOINT_FACE", "").strip()
    or os.getenv("FACE_ENDPOINT_ID", "").strip()
)
REQUEST_TIMEOUT_SECONDS = int(os.getenv("FACE_REQUEST_TIMEOUT", "900"))


def as_data_uri(uploaded_file) -> str:
    """Convert a Streamlit upload into a RunPod-compatible data URI."""
    content_type = uploaded_file.type or "application/octet-stream"
    encoded = base64.b64encode(uploaded_file.getvalue()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def run_face_generation(
    image_uri: str,
    audio_uri: str,
    enhancer: bool,
    resolution: str,
    timeout_seconds: int,
) -> Dict[str, Any]:
    """Submit a face-generation job and wait for the RunPod result."""
    if not RUNPOD_API_KEY:
        raise RuntimeError("RUNPOD_API_KEY is not configured in Replit Secrets.")
    if not RUNPOD_ENDPOINT_FACE:
        raise RuntimeError(
            "RUNPOD_ENDPOINT_FACE or FACE_ENDPOINT_ID is not configured in Replit Secrets."
        )

    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": {
            "face_image_url": image_uri,
            "audio_url": audio_uri,
            "enhancer": enhancer,
            "resolution": resolution,
            "pipeline": "liveportrait+codeformer" if enhancer else "liveportrait",
            "output_format": "mp4",
            "fps": 30,
            "batch_size": 1,
        }
    }

    response = requests.post(
        f"{RUNPOD_API_URL}/{RUNPOD_ENDPOINT_FACE}/runsync",
        headers=headers,
        json=payload,
        timeout=min(timeout_seconds, 60),
    )
    response.raise_for_status()
    result = response.json()

    job_id = result.get("id")
    if job_id and result.get("status") not in {"COMPLETED", "FAILED"}:
        started_at = time.monotonic()
        while time.monotonic() - started_at < timeout_seconds:
            status_response = requests.get(
                f"{RUNPOD_API_URL}/{RUNPOD_ENDPOINT_FACE}/status/{job_id}",
                headers=headers,
                timeout=30,
            )
            status_response.raise_for_status()
            result = status_response.json()
            if result.get("status") in {"COMPLETED", "FAILED"}:
                break
            time.sleep(3)
        else:
            raise TimeoutError(f"Face job {job_id} exceeded {timeout_seconds} seconds.")

    if result.get("status") == "FAILED" or result.get("error"):
        raise RuntimeError(result.get("error", "RunPod face-generation job failed."))

    output = result.get("output", result)
    if isinstance(output, dict):
        video_value = output.get("video_url") or output.get("video_base64") or output.get("output")
    else:
        video_value = output
    if not video_value:
        raise RuntimeError(f"RunPod returned no video output: {result}")

    return {"video": video_value, "job_id": job_id, "raw": result}


def video_bytes(video_value: str) -> bytes | None:
    """Decode a data URI result; URL results are rendered remotely by Streamlit."""
    if not isinstance(video_value, str) or not video_value.startswith("data:"):
        return None
    try:
        encoded = video_value.split(",", 1)[1]
        return base64.b64decode(encoded, validate=True)
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"Invalid video data returned by RunPod: {exc}") from exc


st.set_page_config(page_title="ZOVIX Face Engine Test", page_icon="🎬", layout="centered")
st.title("ZOVIX Face Engine")
st.caption("Replit testing UI -> RunPod GPU inference")

with st.sidebar:
    st.subheader("Endpoint")
    st.write("Configured" if RUNPOD_API_KEY and RUNPOD_ENDPOINT_FACE else "Missing Secrets")
    st.code(RUNPOD_ENDPOINT_FACE or "not configured")
    st.caption("Set secrets in Replit: RUNPOD_API_KEY and RUNPOD_ENDPOINT_FACE")

face_file = st.file_uploader("Face image", type=["png", "jpg", "jpeg", "webp"])
audio_file = st.file_uploader("Driving audio", type=["wav", "mp3", "ogg", "m4a"])
col_left, col_right = st.columns(2)
with col_left:
    resolution = st.selectbox("Resolution", ["512x512", "768x768", "1024x1024"], index=1)
with col_right:
    enhancer = st.checkbox("CodeFormer enhancement", value=False)

if st.button("Generate test video", type="primary", use_container_width=True):
    if not face_file or not audio_file:
        st.error("Please upload both a face image and driving audio.")
    else:
        try:
            with st.spinner("Running face generation on the GPU endpoint..."):
                result = run_face_generation(
                    as_data_uri(face_file),
                    as_data_uri(audio_file),
                    enhancer,
                    resolution,
                    REQUEST_TIMEOUT_SECONDS,
                )
            output_value = result["video"]
            output_bytes = video_bytes(output_value)
            job_suffix = f" ({result['job_id']})" if result["job_id"] else ""
            st.success(f"Generation complete{job_suffix}.")
            if output_bytes:
                st.video(output_bytes)
                st.download_button(
                    "Download MP4",
                    data=output_bytes,
                    file_name="zovix_face_test.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )
            elif isinstance(output_value, str) and output_value.startswith(("http://", "https://")):
                st.video(output_value)
                st.link_button("Open generated video", output_value, use_container_width=True)
            else:
                st.warning("The endpoint returned an unsupported video format.")
        except Exception as exc:
            st.error(str(exc))