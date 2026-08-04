"""
==========================================================================
ZOVIX PRODUCTION MEDIA ENGINE - RunPod Infrastructure
==========================================================================
Models:       LivePortrait + CodeFormer/GFPGAN | XTTS-v2 / MeloTTS
Cost Target:  Under Rs. 0.50 per video/voice generation
Languages:    Bhojpuri, Hindi, Bengali, Tamil, Telugu, Gujarati + more
==========================================================================
"""

import os
import io
import json
import time
import uuid
import base64
import logging
import requests
import hashlib
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime

# ==========================================================================
# CONFIGURATION
# ==========================================================================

logger = logging.getLogger("ZovixProductionEngine")

# RunPod API Configuration
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID_FACE = os.getenv("RUNPOD_ENDPOINT_FACE", "")
RUNPOD_ENDPOINT_ID_VOICE = os.getenv("RUNPOD_ENDPOINT_VOICE", "")
RUNPOD_BASE_URL = "https://api.runpod.ai/v2"

# Cloud Storage
CLOUD_STORAGE_URL = os.getenv("CLOUD_STORAGE_URL", "https://storage.zovix.ai")

# Cost Targets
COST_PER_FACE_VIDEO = 0.006
COST_PER_VOICE_GEN = 0.004

# Language Support Matrix
LANGUAGE_SUPPORT = {
    "english": {"code": "en", "xtts": True, "melo": True, "region": "Global"},
    "hindi": {"code": "hi", "xtts": True, "melo": True, "region": "India"},
    "bhojpuri": {"code": "bho", "xtts": True, "melo": False, "region": "India"},
    "bengali": {"code": "bn", "xtts": True, "melo": True, "region": "India"},
    "tamil": {"code": "ta", "xtts": True, "melo": True, "region": "India"},
    "telugu": {"code": "te", "xtts": True, "melo": True, "region": "India"},
    "gujarati": {"code": "gu", "xtts": True, "melo": False, "region": "India"},
    "marathi": {"code": "mr", "xtts": True, "melo": False, "region": "India"},
    "punjabi": {"code": "pa", "xtts": True, "melo": False, "region": "India"},
    "urdu": {"code": "ur", "xtts": True, "melo": False, "region": "India"},
    "kannada": {"code": "kn", "xtts": True, "melo": False, "region": "India"},
    "malayalam": {"code": "ml", "xtts": True, "melo": False, "region": "India"},
    "odia": {"code": "or", "xtts": True, "melo": False, "region": "India"},
    "assamese": {"code": "as", "xtts": True, "melo": False, "region": "India"},
}

# Emotion prompts for XTTS
EMOTION_PROMPTS = {
    "neutral": "Speak in a neutral, calm tone.",
    "happy": "Speak with happiness and joy in your voice.",
    "sad": "Speak with a sad, melancholic tone.",
    "angry": "Speak with anger and frustration.",
    "excited": "Speak with excitement and enthusiasm.",
    "fearful": "Speak with fear and anxiety in your voice.",
    "surprised": "Speak with surprise and amazement.",
    "whisper": "Speak in a soft whisper.",
    "shout": "Speak loudly with a shouting tone.",
    "authoritative": "Speak with authority and confidence.",
    "soothing": "Speak in a calming, soothing voice.",
    "sale_pitch": "Speak with persuasive, energetic sales pitch tone.",
    "customer_care": "Speak with polite, helpful customer service tone.",
}

# ==========================================================================
# RUNPOD CLIENT
# ==========================================================================

class RunPodClient:
    """RunPod API client for serverless endpoints"""

    def __init__(self):
        self.api_key = RUNPOD_API_KEY
        self.base_url = RUNPOD_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def run_sync(self, endpoint_id: str, payload: Dict[str, Any],
                 timeout: int = 300, poll_interval: int = 2) -> Dict[str, Any]:
        """Run a serverless endpoint synchronously with polling"""

        if not endpoint_id:
            raise ValueError("RunPod endpoint ID is not configured")

        start_time = time.time()

        # Try runsync first
        try:
            submit_url = f"{self.base_url}/{endpoint_id}/runsync"
            resp = requests.post(submit_url, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            if "output" in result and result.get("status") == "COMPLETED":
                elapsed = time.time() - start_time
                logger.info(f"RunPod sync completed in {elapsed:.2f}s: {endpoint_id}")
                return result

            job_id = result.get("id")
            if job_id:
                return self._poll_job(endpoint_id, job_id, timeout, poll_interval, start_time)
            return result

        except (requests.exceptions.Timeout, Exception) as e:
            logger.warning(f"Runsync failed, falling back to async+poll: {e}")
            return self._run_async_fallback(endpoint_id, payload, timeout, poll_interval)

    def _run_async_fallback(self, endpoint_id: str, payload: Dict[str, Any],
                            timeout: int, poll_interval: int) -> Dict[str, Any]:
        """Fallback to async run + polling"""
        start_time = time.time()
        run_url = f"{self.base_url}/{endpoint_id}/run"

        resp = requests.post(run_url, headers=self.headers, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        job_id = result.get("id")

        if not job_id:
            raise RuntimeError(f"No job ID returned: {result}")

        return self._poll_job(endpoint_id, job_id, timeout, poll_interval, start_time)

    def _poll_job(self, endpoint_id: str, job_id: str, timeout: int,
                  poll_interval: int, start_time: float) -> Dict[str, Any]:
        """Poll job status until completion"""
        status_url = f"{self.base_url}/{endpoint_id}/status/{job_id}"

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Job timed out after {timeout}s: {job_id}")

            resp = requests.get(status_url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            status = result.get("status", "IN_QUEUE")

            if status == "COMPLETED":
                logger.info(f"Job completed in {elapsed:.2f}s: {job_id}")
                return result

            if status == "FAILED":
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Job failed: {job_id} - {error_msg}")
                raise RuntimeError(f"RunPod job failed: {error_msg}")

            time.sleep(poll_interval)

    def check_health(self, endpoint_id: str) -> Dict[str, Any]:
        """Check endpoint health"""
        if not endpoint_id:
            return {"status": "not_configured"}
        try:
            url = f"{self.base_url}/{endpoint_id}/health"
            resp = requests.get(url, headers=self.headers, timeout=10)
            return {
                "status": "healthy" if resp.status_code == 200 else "unhealthy",
                "response": resp.json() if resp.status_code == 200 else resp.text
            }
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}


runpod_client = RunPodClient()


# ==========================================================================
# 1. FACE VIDEO ENGINE - LivePortrait + CodeFormer
# ==========================================================================

def generate_production_face_video(
    face_image_url: str,
    audio_url: str,
    enhancer: bool = True,
    resolution: str = "1024x1024",
    quality: str = "ultra",
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Generate hyper-realistic face video using LivePortrait + CodeFormer on RunPod

    Args:
        face_image_url: Public URL of the face image
        audio_url: Public URL of the audio file
        enhancer: Apply CodeFormer/GFPGAN 4K enhancement
        resolution: Output video resolution
        quality: Generation quality (ultra | standard | fast)
        timeout: Maximum wait time in seconds

    Returns:
        Dict with video_url, latency_ms, cost, resolution
    """
    start_time = time.time()
    logger.info(f"Starting face video generation: enhancer={enhancer}, resolution={resolution}")

    payload = {
        "input": {
            "face_image_url": face_image_url,
            "audio_url": audio_url,
            "enhancer": enhancer,
            "resolution": resolution,
            "quality": quality,
            "pipeline": "liveportrait+codeformer" if enhancer else "liveportrait",
            "output_format": "mp4",
            "fps": 30,
            "batch_size": 1
        }
    }

    result = runpod_client.run_sync(RUNPOD_ENDPOINT_ID_FACE, payload, timeout=timeout, poll_interval=3)

    output = result.get("output", {})
    if isinstance(output, str):
        video_url = output
    elif isinstance(output, dict):
        video_url = output.get("video_url", output.get("output", ""))
    else:
        video_url = str(output)

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        "video_url": video_url,
        "latency_ms": round(elapsed_ms, 2),
        "cost": COST_PER_FACE_VIDEO,
        "cost_inr": round(COST_PER_FACE_VIDEO * 83, 2),
        "resolution": resolution,
        "enhancer_applied": enhancer,
        "timestamp": datetime.now().isoformat()
    }


# ==========================================================================
# 2. VOICE / TTS ENGINE - XTTS-v2 Multilingual
# ==========================================================================

def generate_production_voice(
    text: str,
    language: str = "hindi",
    speaker_audio_url: Optional[str] = None,
    emotion: str = "neutral",
    speed: float = 1.0,
    pitch: float = 1.0,
    output_format: str = "mp3",
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Generate multilingual voice using XTTS-v2 on RunPod

    Args:
        text: Text to convert to speech
        language: Target language (hindi, bhojpuri, bengali, tamil, telugu, etc.)
        speaker_audio_url: Optional URL for voice cloning reference
        emotion: Emotional tone for the voice
        speed: Speech speed multiplier (0.5 - 2.0)
        pitch: Voice pitch multiplier (0.5 - 2.0)
        output_format: Output audio format
        timeout: Maximum wait time in seconds

    Returns:
        Dict with audio_url, latency_ms, cost, language, duration_sec
    """
    lang_lower = language.lower().strip()

    if lang_lower not in LANGUAGE_SUPPORT:
        supported = list(LANGUAGE_SUPPORT.keys())
        raise ValueError(f"Unsupported language: {language}. Supported: {supported}")

    lang_info = LANGUAGE_SUPPORT[lang_lower]
    lang_code = lang_info["code"]

    if emotion.lower() not in EMOTION_PROMPTS:
        emotion = "neutral"

    start_time = time.time()
    logger.info(f"Starting voice generation: lang={lang_lower}, emotion={emotion}, speed={speed}")

    estimated_duration = max(1, len(text) / 15)
    emotion_text = EMOTION_PROMPTS.get(emotion.lower(), EMOTION_PROMPTS["neutral"])

    payload = {
        "input": {
            "text": text,
            "language": lang_code,
            "language_name": lang_lower,
            "speaker_audio_url": speaker_audio_url or "",
            "emotion": emotion.lower(),
            "emotion_prompt": emotion_text,
            "speed": speed,
            "pitch": pitch,
            "output_format": output_format,
            "model": "xtts-v2",
            "enhance_audio": True
        }
    }

    result = runpod_client.run_sync(RUNPOD_ENDPOINT_ID_VOICE, payload, timeout=timeout, poll_interval=2)

    output = result.get("output", {})
    if isinstance(output, str):
        audio_url = output
    elif isinstance(output, dict):
        audio_url = output.get("audio_url", output.get("output", ""))
    else:
        audio_url = str(output)

    elapsed_ms = (time.time() - start_time) * 1000

    return {
        "audio_url": audio_url,
        "latency_ms": round(elapsed_ms, 2),
        "cost": COST_PER_VOICE_GEN,
        "cost_inr": round(COST_PER_VOICE_GEN * 83, 2),
        "language": lang_lower,
        "language_code": lang_code,
        "emotion": emotion.lower(),
        "duration_sec": round(estimated_duration, 1),
        "text_length": len(text),
        "timestamp": datetime.now().isoformat()
    }


# ==========================================================================
# 3. STREAMLIT COMPATIBILITY WRAPPERS
# ==========================================================================

def generate_production_face_video_streamlit(image_url, audio_url, enhancer=True, st_instance=None):
    """Streamlit-compatible wrapper for face video generation"""
    if st_instance:
        with st_instance.spinner("Generating hyper-realistic face video on RunPod GPU..."):
            return generate_production_face_video(image_url, audio_url, enhancer=enhancer)
    return generate_production_face_video(image_url, audio_url, enhancer=enhancer)


def generate_production_voice_streamlit(text, language="hindi", speaker_audio_url=None,
                                        emotion="neutral", st_instance=None):
    """Streamlit-compatible wrapper for voice generation"""
    if st_instance:
        with st_instance.spinner(f"Generating {language} voice on RunPod GPU..."):
            return generate_production_voice(text, language, speaker_audio_url, emotion)
    return generate_production_voice(text, language, speaker_audio_url, emotion)


# ==========================================================================
# 4. UTILITY FUNCTIONS
# ==========================================================================

def get_language_list() -> Dict[str, Dict[str, Any]]:
    """Get list of supported languages with metadata"""
    return {
        name: {
            "code": info["code"],
            "xtts_supported": info["xtts"],
            "melo_supported": info["melo"],
            "region": info["region"]
        }
        for name, info in LANGUAGE_SUPPORT.items()
    }


def get_emotion_list() -> list:
    """Get list of supported emotions"""
    return list(EMOTION_PROMPTS.keys())


def check_endpoint_health(endpoint_id: str) -> Dict[str, Any]:
    """Check health status of a RunPod endpoint"""
    return runpod_client.check_health(endpoint_id)


def get_cost_estimate(video_count: int = 1000, voice_count: int = 10000) -> Dict[str, Any]:
    """Get cost estimates for production volumes"""
    video_cost_usd = video_count * COST_PER_FACE_VIDEO
    voice_cost_usd = voice_count * COST_PER_VOICE_GEN
    total_usd = video_cost_usd + voice_cost_usd
    inr_rate = 83

    return {
        "video": {
            "count": video_count,
            "cost_per_video_usd": COST_PER_FACE_VIDEO,
            "cost_per_video_inr": round(COST_PER_FACE_VIDEO * inr_rate, 2),
            "total_usd": round(video_cost_usd, 2),
            "total_inr": round(video_cost_usd * inr_rate, 2)
        },
        "voice": {
            "count": voice_count,
            "cost_per_voice_usd": COST_PER_VOICE_GEN,
            "cost_per_voice_inr": round(COST_PER_VOICE_GEN * inr_rate, 2),
            "total_usd": round(voice_cost_usd, 2),
            "total_inr": round(voice_cost_usd * inr_rate, 2)
        },
        "total": {
            "usd": round(total_usd, 2),
            "inr": round(total_usd * inr_rate, 2)
        }
    }
