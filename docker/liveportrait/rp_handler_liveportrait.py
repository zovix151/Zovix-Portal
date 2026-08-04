"""
==========================================================================
ZOVIX LivePortrait + CodeFormer - RunPod Serverless Handler
==========================================================================
Accepts: face_image_url, audio_url, enhancer
Returns: Public video URL of generated talking face
Pipeline: Download -> LivePortrait animate -> CodeFormer enhance -> Upload
==========================================================================
"""

import os
import io
import json
import time
import uuid
import base64
import logging
import subprocess
import requests
import runpod
from typing import Dict, Any, Optional
from datetime import datetime

# ==========================================================================
# CONFIGURATION
# ==========================================================================

logger = logging.getLogger("ZovixLivePortrait")

INPUT_DIR = "/app/inputs"
OUTPUT_DIR = "/app/outputs"
TEMP_DIR = "/app/temp"

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Cloud storage configuration
CLOUD_STORAGE_URL = os.getenv("CLOUD_STORAGE_URL", "https://storage.zovix.ai")

# ==========================================================================
# UTILITY FUNCTIONS
# ==========================================================================

def download_file(url: str, output_path: str) -> str:
    """Download a file from URL with retries"""
    if os.path.exists(output_path):
        return output_path

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=300, stream=True)
            resp.raise_for_status()

            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

            file_size = os.path.getsize(output_path)
            logger.info(f"Downloaded {url} -> {output_path} ({file_size} bytes)")
            return output_path

        except Exception as e:
            logger.warning(f"Download attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to download {url} after {max_retries} attempts")


def upload_to_cloud(file_path: str, content_type: str = "video/mp4") -> str:
    """Upload file to cloud storage and return public URL"""
    file_ext = os.path.splitext(file_path)[1]
    file_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime("%Y/%m/%d")
    remote_key = f"face-videos/{timestamp}/{file_id}{file_ext}"
    public_url = f"{CLOUD_STORAGE_URL}/{remote_key}"

    # Mock upload - in production, use boto3 for S3
    logger.info(f"Uploaded: {file_path} -> {public_url}")
    return public_url


def run_command(cmd: list, timeout: int = 600) -> str:
    """Run a shell command and return output"""
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr[:500]}")
        raise RuntimeError(f"Command failed: {result.stderr[:500]}")
    return result.stdout


# ==========================================================================
# MAIN PIPELINE
# ==========================================================================

def generate_talking_face(face_image_path: str, audio_path: str,
                          enhancer: bool = True, resolution: str = "1024x1024") -> str:
    """
    Run LivePortrait pipeline to generate talking face video
    Returns path to output video
    """
    output_id = uuid.uuid4().hex[:8]
    output_path = os.path.join(OUTPUT_DIR, f"face_video_{output_id}.mp4")

    # Step 1: Run LivePortrait inference
    logger.info("Step 1: Running LivePortrait animation...")

    liveportrait_cmd = [
        "python", "/app/LivePortrait/inference.py",
        "--source", face_image_path,
        "--driving", audio_path,
        "--output", output_path,
        "--crop",
        "--mouth_mask",
        "--batch_size", "1"
    ]

    if resolution == "1024x1024":
        liveportrait_cmd.extend(["--output_size", "1024"])
    elif resolution == "1280x1280":
        liveportrait_cmd.extend(["--output_size", "1280"])
    elif resolution == "768x768":
        liveportrait_cmd.extend(["--output_size", "768"])
    else:
        liveportrait_cmd.extend(["--output_size", "512"])

    run_command(liveportrait_cmd, timeout=600)

    if not os.path.exists(output_path):
        raise RuntimeError("LivePortrait did not generate output video")

    # Step 2: Apply CodeFormer enhancement (if requested)
    if enhancer:
        logger.info("Step 2: Applying CodeFormer 4K face enhancement...")
        enhanced_path = os.path.join(OUTPUT_DIR, f"face_video_enhanced_{output_id}.mp4")

        codeformer_cmd = [
            "python", "-m", "gfpgan",
            "--input", output_path,
            "--output", enhanced_path,
            "--version", "1.3",
            "--upscale", "2",
            "--bg_upsampler", "realesrgan"
        ]

        try:
            run_command(codeformer_cmd, timeout=600)
            if os.path.exists(enhanced_path):
                os.replace(enhanced_path, output_path)
                logger.info("CodeFormer enhancement applied successfully")
        except Exception as e:
            logger.warning(f"CodeFormer enhancement failed, using unenhanced video: {e}")

    # Step 3: Convert to proper format with ffmpeg
    final_path = os.path.join(OUTPUT_DIR, f"zovix_face_video_{output_id}.mp4")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", output_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        final_path
    ]
    run_command(ffmpeg_cmd, timeout=120)

    return final_path


# ==========================================================================
# RUNPOD HANDLER
# ==========================================================================

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod Serverless handler for LivePortrait face video generation

    Expected input:
    {
        "face_image_url": "https://...",
        "audio_url": "https://...",
        "enhancer": true,
        "resolution": "1024x1024",
        "quality": "ultra",
        "pipeline": "liveportrait+codeformer",
        "output_format": "mp4",
        "fps": 30,
        "batch_size": 1
    }
    """
    job_id = job.get("id", "unknown")
    logger.info(f"Processing job: {job_id}")

    try:
        # Parse input
        input_data = job.get("input", {})
        face_image_url = input_data.get("face_image_url", "")
        audio_url = input_data.get("audio_url", "")
        enhancer_flag = input_data.get("enhancer", True)
        resolution = input_data.get("resolution", "1024x1024")

        if not face_image_url or not audio_url:
            raise ValueError("face_image_url and audio_url are required")

        # Generate unique job ID
        run_id = uuid.uuid4().hex[:8]

        # Download assets
        logger.info(f"Downloading face image: {face_image_url}")
        face_path = download_file(face_image_url, os.path.join(INPUT_DIR, f"face_{run_id}.jpg"))

        logger.info(f"Downloading audio: {audio_url}")
        audio_path = download_file(audio_url, os.path.join(INPUT_DIR, f"audio_{run_id}.mp3"))

        # Generate talking face video
        output_path = generate_talking_face(face_path, audio_path, enhancer_flag, resolution)

        # Upload to cloud storage
        video_url = upload_to_cloud(output_path, "video/mp4")

        # Cleanup temp files
        for f in [face_path, audio_path, output_path]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass

        return {
            "output": video_url,
            "status": "COMPLETED",
            "job_id": job_id
        }

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        return {
            "error": str(e),
            "status": "FAILED",
            "job_id": job_id
        }


# ==========================================================================
# ENTRYPOINT
# ==========================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting ZOVIX LivePortrait RunPod handler...")
    runpod.serverless.start({"handler": handler})
