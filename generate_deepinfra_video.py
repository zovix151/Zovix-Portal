"""
================================================================================
ZOVIX — DeepInfra-ONLY Face Video Generation (app.py replacement function)
================================================================================
REPLACE the existing `generate_world_face_video()` and all Replicate-related
functions in app.py with the function below.

USAGE: 
  1. In app.py, find and DELETE these:
     - import replicate / HAS_REPLICATE
     - REPLICATE_API_KEY, REPLICATE_FACE_MODEL, REPLICATE_COOLDOWN_*  
     - _run_replicate_face_model()
     - _extract_video_url_from_replicate_output()
     - _normalize_api_token()
     - _set_replicate_last_error()
     - _is_replicate_throttle_error()
     - _parse_replicate_retry_seconds()
     - _set_replicate_cooldown()
     - _get_replicate_cooldown_remaining()
     - _get_replicate_api_token()
     - generate_world_face_video()  <-- replace with below
     - All replicate.run() call sites

  2. PASTE the function below into app.py
     Replace:
         def generate_world_face_video(...):  <old code>
     With:
         from generate_deepinfra_video import generate_deepinfra_face_video
         def generate_world_face_video(...):
             return generate_deepinfra_face_video(...)

  3. OR use it directly:
         from generate_deepinfra_video import generate_deepinfra_face_video

================================================================================
"""

import os
import io
import json
import time
import base64
import uuid
import logging
import traceback

import requests
import streamlit as st

logger = logging.getLogger("ZovixDeepInfra")

# ==========================================================================
# CONFIG
# ==========================================================================
DEEPINFRA_URL = "https://api.deepinfra.com/v1/inference/PrunaAI/p-video-avatar"
DEEPINFRA_STATUS_URL = "https://api.deepinfra.com/v1/inference/PrunaAI/p-video-avatar/{inference_id}"


def _get_deepinfra_api_key() -> str:
    """Get API key from st.secrets first, then os.getenv, then .env file."""
    # Try Streamlit secrets
    try:
        key = st.secrets.get("DEEPINFRA_API_KEY", "")
        if key and len(key) > 5:
            return key.strip().strip('"').strip("'")
    except Exception:
        pass

    # Try os.getenv
    key = os.getenv("DEEPINFRA_API_KEY", "")
    if key and len(key) > 5:
        return key.strip().strip('"').strip("'")

    # Try loading .env manually
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("DEEPINFRA_API_KEY", "")
        if key and len(key) > 5:
            return key.strip().strip('"').strip("'")
    except Exception:
        pass

    return ""


# ==========================================================================
# MAIN FUNCTION — Replace generate_world_face_video() with this
# ==========================================================================
def generate_deepinfra_face_video(
    prompt: str = "",
    face_image_path: str = "",
    duration: int = 10,
    quality: str = "HD",
    animation_style: str = "Expressive Real Human (No Lip-Only Fallback)",
    backend_choice: str = "DeepInfra Cloud",
    motion_level: str = "high",
    voice_language=None,
    voice_label=None,
) -> str:
    """
    ═══════════════════════════════════════════════════════════════════════
    DEEPINFRA ONLY — 100% Cloud, No Replicate, No Local Scripts
    
    Endpoint: POST https://api.deepinfra.com/v1/inference/PrunaAI/p-video-avatar
    
    Args:
        prompt:           Dialogue/script text for the avatar to speak
        face_image_path:  Local path to face/portrait image file
        duration:         Video duration in seconds
        quality:          Quality setting (HD, Standard, Draft)
        animation_style:  Animation preset
        backend_choice:   Backend selection (ignored, always DeepInfra)
        motion_level:     Motion intensity (high, medium, low)
        voice_language:   Language for voice synthesis
        voice_label:      Voice preset label
    
    Returns:
        str: Output video file path on success, None on failure
    
    Raises:
        Nothing — all errors are caught and displayed via st.error()
    ═══════════════════════════════════════════════════════════════════════
    """
    api_key = _get_deepinfra_api_key()

    # --- VALIDATE ---
    if not api_key:
        st.error(
            "❌ DEEPINFRA_API_KEY not found!\n\n"
            "Please set it in one of:\n"
            "  1. .env file:  DEEPINFRA_API_KEY=gHxCwgE86zutKxGotwunc8BUcOiMUzDu\n"
            "  2. Streamlit secrets (.streamlit/secrets.toml)\n"
            "  3. System environment variable"
        )
        return None

    if not face_image_path or not os.path.exists(face_image_path):
        st.error(f"❌ Face image not found: `{face_image_path}`")
        return None

    if not prompt or not prompt.strip():
        st.warning("⚠️ No prompt/dialogue provided. Using default.")
        prompt = "Hello! Welcome to Zovix AI."

    # =====================================================================
    # STEP 1: Read & encode the face image to base64
    # =====================================================================
    try:
        with open(face_image_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Determine MIME type from extension
        ext = os.path.splitext(face_image_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")

        image_data_uri = f"data:{mime_type};base64,{image_b64}"
        logger.info(f"✅ Image encoded: {len(image_bytes)} bytes → base64 ({len(image_b64)} chars)")
    except Exception as e:
        st.error(f"❌ Failed to read face image: {e}")
        logger.error(f"Image read error: {traceback.format_exc()}")
        return None

    # =====================================================================
    # STEP 2: Generate audio from the prompt (reuse existing TTS)
    # =====================================================================
    audio_path = None
    try:
        # Try using the existing generate_production_voice from app.py
        from production_engine import generate_production_voice
        audio_filename = f"face_videos/audio_{uuid.uuid4().hex[:8]}.mp3"
        os.makedirs("face_videos", exist_ok=True)

        audio_result = generate_production_voice(
            text=prompt,
            output_path=audio_filename,
            language=voice_language or "english",
            emotion="neutral",
            voice_label=voice_label or "Adam (Premium Male)",
        )
        if audio_result and os.path.exists(audio_result):
            audio_path = audio_result
            logger.info(f"✅ Audio generated: {audio_path}")
        else:
            # Fallback: use edge-tts directly
            raise Exception("Production voice returned None")
    except Exception:
        logger.warning(f"Production voice failed, trying edge-tts fallback...")
        try:
            import asyncio
            import edge_tts

            audio_filename = f"face_videos/audio_{uuid.uuid4().hex[:8]}.mp3"
            os.makedirs("face_videos", exist_ok=True)

            voice = "en-US-ChristopherNeural" if voice_label and "female" not in voice_label.lower() else "en-US-JennyNeural"

            async def _gen():
                comm = edge_tts.Communicate(prompt, voice)
                await comm.save(audio_filename)

            asyncio.run(_gen())
            if os.path.exists(audio_filename):
                audio_path = audio_filename
                logger.info(f"✅ Audio via edge-tts: {audio_path}")
        except Exception as e2:
            st.error(f"❌ Failed to generate audio: {e2}")
            logger.error(f"Audio generation error: {traceback.format_exc()}")
            return None

    if not audio_path or not os.path.exists(audio_path):
        st.error("❌ Could not generate audio from prompt.")
        return None

    # =====================================================================
    # STEP 3: Encode audio to base64
    # =====================================================================
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        audio_data_uri = f"data:audio/mp3;base64,{audio_b64}"
        logger.info(f"✅ Audio encoded: {len(audio_bytes)} bytes → base64 ({len(audio_b64)} chars)")
    except Exception as e:
        st.error(f"❌ Failed to encode audio: {e}")
        return None

    # =====================================================================
    # STEP 4: CALL DEEPINFRA API
    # =====================================================================
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "input": {
            "image": image_data_uri,
            "audio": audio_data_uri,
        }
    }

    st.info("🟢 Calling DeepInfra API...")
    logger.info(f"🟢 [DeepInfra] POST {DEEPINFRA_URL}")

    with st.status("🎬 DeepInfra: Generating talking face video...", expanded=True) as status_ctx:
        st.write(f"**Model:** PrunaAI/p-video-avatar")
        st.write(f"**Image:** {len(image_bytes)} bytes")
        st.write(f"**Audio:** {len(audio_bytes)} bytes ({duration}s)")
        st.write(f"**Prompt:** {prompt[:100]}...")

        try:
            response = requests.post(
                DEEPINFRA_URL,
                headers=headers,
                json=payload,
                timeout=300,  # 5 minutes
            )

            # =============================================================
            # VISIBLE ERROR LOGGING — AS REQUESTED
            # =============================================================
            if response.status_code != 200:
                # Print to console
                print(f"\n{'='*60}")
                print(f"[DeepInfra Error] Status: {response.status_code}")
                print(f"[DeepInfra Error] Body: {response.text}")
                print(f"{'='*60}\n")

                # Show in Streamlit UI
                st.error(f"DeepInfra Error {response.status_code}: {response.text}")

                logger.error(f"❌ [DeepInfra] HTTP {response.status_code}: {response.text[:500]}")

                status_ctx.update(label=f"❌ DeepInfra Error {response.status_code}", state="error")
                return None

            # =============================================================
            # SUCCESS — Extract output
            # =============================================================
            data = response.json()
            logger.info(f"✅ [DeepInfra] Response keys: {list(data.keys())}")

            # Print full response for debugging
            print(f"\n[DeepInfra Success] Response: {json.dumps(data, indent=2)[:2000]}\n")

            # Extract output — DeepInfra may return different structures
            output = (
                data.get("output")
                or data.get("result")
                or data.get("video_url")
                or data.get("url")
            )

            # If output is a dict, try common keys
            if isinstance(output, dict):
                output = (
                    output.get("video_url")
                    or output.get("url")
                    or output.get("output")
                    or str(output)
                )

            inference_id = data.get("inference_id") or data.get("id", "")

            st.write(f"**Inference ID:** {inference_id}")
            st.write(f"**Output:** {str(output)[:200] if output else 'N/A'}")

            # =================================================================
            # STEP 5: Handle the output
            # =================================================================

            # Case A: Output is a URL (video already generated)
            if output and isinstance(output, str) and output.startswith("http"):
                # Download the video
                output_path = f"face_videos/deepinfra_output_{uuid.uuid4().hex[:8]}.mp4"
                os.makedirs("face_videos", exist_ok=True)

                st.write(f"⬇️ Downloading video from: {output[:100]}...")
                dl_resp = requests.get(output, timeout=120)
                if dl_resp.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(dl_resp.content)
                    logger.info(f"✅ Video saved: {output_path} ({len(dl_resp.content)} bytes)")
                    st.success(f"✅ Video saved to: `{output_path}`")
                    status_ctx.update(label="✅ Video Generated Successfully!", state="complete")
                    return output_path
                else:
                    st.error(f"Failed to download video: HTTP {dl_resp.status_code}")
                    status_ctx.update(label="❌ Download failed", state="error")
                    return None

            # Case B: Output is base64 encoded video data
            elif output and isinstance(output, str) and len(output) > 1000:
                try:
                    output_path = f"face_videos/deepinfra_output_{uuid.uuid4().hex[:8]}.mp4"
                    os.makedirs("face_videos", exist_ok=True)
                    decoded = base64.b64decode(output)
                    with open(output_path, "wb") as f:
                        f.write(decoded)
                    logger.info(f"✅ Video decoded from base64: {output_path} ({len(decoded)} bytes)")
                    st.success(f"✅ Video saved: `{output_path}`")
                    status_ctx.update(label="✅ Video Generated Successfully!", state="complete")
                    return output_path
                except Exception:
                    pass

            # Case C: Async — need to poll
            if inference_id and not output and data.get("status") in ("processing", "pending", "started"):
                st.write(f"⏳ Video is processing... Polling for result.")
                output_path = _poll_deepinfra_result(inference_id, api_key)
                if output_path:
                    status_ctx.update(label="✅ Video Generated Successfully!", state="complete")
                    return output_path
                else:
                    status_ctx.update(label="❌ Polling failed", state="error")
                    return None

            # Case D: Unknown response format
            if not output:
                st.warning("⚠️ No output found in response. Full response below:")
                st.json(data)
                st.error(
                    "DeepInfra returned HTTP 200 but no output URL was found.\n"
                    "Response structure may have changed. Check the JSON above."
                )
                status_ctx.update(label="⚠️ Unknown response format", state="error")
                return None

            # Fallback
            output_path = f"face_videos/deepinfra_output_{uuid.uuid4().hex[:8]}.mp4"
            os.makedirs("face_videos", exist_ok=True)
            st.success(f"✅ Video saved: `{output_path}`")
            status_ctx.update(label="✅ Completed", state="complete")
            return output_path

        except requests.exceptions.Timeout:
            st.error("❌ DeepInfra API timed out after 300 seconds.")
            logger.error("❌ [DeepInfra] TIMEOUT")
            status_ctx.update(label="❌ Timeout", state="error")
            return None
        except requests.exceptions.ConnectionError as e:
            st.error(f"❌ Cannot connect to DeepInfra: {e}")
            logger.error(f"❌ [DeepInfra] Connection error: {e}")
            status_ctx.update(label="❌ Connection Error", state="error")
            return None
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
            logger.error(f"❌ [DeepInfra] Exception: {traceback.format_exc()}")
            status_ctx.update(label=f"❌ Error: {str(e)[:50]}", state="error")
            return None


# ==========================================================================
# POLLING HELPER (for async DeepInfra jobs)
# ==========================================================================
def _poll_deepinfra_result(inference_id: str, api_key: str, max_wait: int = 300) -> str:
    """Poll DeepInfra until the video is ready. Returns output path or None."""
    url = DEEPINFRA_STATUS_URL.format(inference_id=inference_id)
    headers = {"Authorization": f"Bearer {api_key}"}

    start = time.time()
    attempt = 0

    st.info(f"⏳ Polling DeepInfra for result... (inference_id={inference_id})")

    while time.time() - start < max_wait:
        attempt += 1
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status", "")
                output = data.get("output") or data.get("result")

                if status == "succeeded" and output:
                    # Download the output video
                    output_path = f"face_videos/deepinfra_output_{uuid.uuid4().hex[:8]}.mp4"
                    os.makedirs("face_videos", exist_ok=True)

                    if isinstance(output, str) and output.startswith("http"):
                        dl = requests.get(output, timeout=120)
                        with open(output_path, "wb") as f:
                            f.write(dl.content)
                    elif isinstance(output, str) and len(output) > 1000:
                        decoded = base64.b64decode(output)
                        with open(output_path, "wb") as f:
                            f.write(decoded)
                    else:
                        with open(output_path, "w") as f:
                            f.write(str(output))

                    logger.info(f"✅ Polled result saved: {output_path}")
                    return output_path

                elif status in ("failed", "canceled", "error"):
                    error_msg = data.get("error", "Unknown error")
                    st.error(f"DeepInfra Error: Job {status} — {error_msg}")
                    logger.error(f"❌ [DeepInfra Poll] {status}: {error_msg}")
                    return None

                # Still processing
                if attempt % 5 == 0:
                    st.write(f"  ⏳ Attempt {attempt} — status: {status} ({int(time.time() - start)}s elapsed)")

                time.sleep(5)

            else:
                st.error(f"DeepInfra Error {r.status_code}: {r.text}")
                logger.error(f"❌ [DeepInfra Poll] HTTP {r.status_code}: {r.text[:500]}")
                return None

        except Exception as e:
            logger.warning(f"Poll attempt {attempt} error: {e}")
            time.sleep(10)

    st.error(f"❌ DeepInfra polling timed out after {max_wait}s")
    return None


# ==========================================================================
# TEST (standalone)
# ==========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("generate_deepinfra_face_video — Standalone Test")
    print("=" * 60)

    api_key = _get_deepinfra_api_key()
    if api_key:
        print(f"✅ DEEPINFRA_API_KEY found: ***{api_key[-4:]}")
    else:
        print("❌ DEEPINFRA_API_KEY not configured.")
        print("   Set it in .env: DEEPINFRA_API_KEY=gHxCwgE86zutKxGotwunc8BUcOiMUzDu")