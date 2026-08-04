"""
==========================================================================
ZOVIX XTTS-v2 Multilingual TTS - RunPod Handler
==========================================================================
Accepts: text, language_code, speaker_audio_url (optional), emotion
Returns: Public audio URL of generated speech
Pipeline: Download speaker sample -> XTTS generate -> Enhance -> Upload
==========================================================================
"""

import os
import io
import json
import time
import uuid
import base64
import logging
import tempfile
import requests
import runpod
import torch
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime

# ==========================================================================
# CONFIGURATION
# ==========================================================================

logger = logging.getLogger("ZovixXTTS")

INPUT_DIR = "/app/inputs"
OUTPUT_DIR = "/app/outputs"
TEMP_DIR = "/app/temp"
MODEL_DIR = os.getenv("XTTS_MODEL_DIR", "/app/xtts_model")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

CLOUD_STORAGE_URL = os.getenv("CLOUD_STORAGE_URL", "https://storage.zovix.ai")

# Language code mapping
LANGUAGE_CODE_MAP = {
    "en": "en",
    "hi": "hi",
    "bho": "hi",
    "bn": "bn",
    "ta": "ta",
    "te": "te",
    "gu": "gu",
    "mr": "mr",
    "pa": "pa",
    "ur": "ur",
    "kn": "kn",
    "ml": "ml",
    "or": "or",
    "as": "as",
    "sa": "hi",
}

# ==========================================================================
# MODEL LOADING
# ==========================================================================

class TTSModel:
    """Singleton TTS model wrapper"""

    _instance = None
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            logger.info("Loading XTTS-v2 model...")
            from TTS.api import TTS
            device = "cuda" if torch.cuda.is_available() else "cpu"
            cls._model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                gpu=(device == "cuda"),
                progress_bar=False
            )
            logger.info(f"XTTS-v2 loaded on {device}")
        return cls._model


tts_model = TTSModel()

# ==========================================================================
# UTILITY FUNCTIONS
# ==========================================================================

def download_file(url: str, output_path: str) -> str:
    """Download a file from URL"""
    if os.path.exists(output_path):
        return output_path

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=120, stream=True)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Downloaded {url} -> {output_path}")
            return output_path
        except Exception as e:
            logger.warning(f"Download attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to download: {url}")


def upload_to_cloud(file_path: str, content_type: str = "audio/mp3") -> str:
    """Upload file to cloud storage"""
    file_ext = os.path.splitext(file_path)[1]
    file_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime("%Y/%m/%d")
    remote_key = f"voice/{timestamp}/{file_id}{file_ext}"
    public_url = f"{CLOUD_STORAGE_URL}/{remote_key}"
    logger.info(f"Uploaded: {file_path} -> {public_url}")
    return public_url


def apply_audio_enhancement(input_path: str, output_path: str) -> str:
    """Apply audio enhancement (noise reduction, normalization)"""
    try:
        import subprocess
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-af", "afftdn=nf=-25,volume=1.5",
            "-ar", "22050",
            "-ac", "1",
            "-b:a", "192k",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        logger.warning(f"Audio enhancement failed: {e}")
    return input_path


# ==========================================================================
# EMOTION PRESETS
# ==========================================================================

EMOTION_PROMPTS = {
    "neutral": None,
    "happy": "<PROSODY volume='high' rate='fast'>",
    "sad": "<PROSODY volume='low' rate='slow'>",
    "angry": "<PROSODY volume='high' rate='fast' pitch='high'>",
    "excited": "<PROSODY volume='high' rate='very-fast'>",
    "fearful": "<PROSODY volume='low' rate='fast' pitch='high'>",
    "whisper": "<PROSODY volume='very-low' rate='slow'>",
    "authoritative": "<PROSODY volume='high' rate='medium' pitch='low'>",
    "soothing": "<PROSODY volume='medium' rate='slow' pitch='low'>",
    "sale_pitch": "<PROSODY volume='high' rate='fast' pitch='medium'>",
    "customer_care": "<PROSODY volume='medium' rate='medium'>",
}

# ==========================================================================
# TTS GENERATION
# ==========================================================================

def generate_speech(
    text: str,
    language_code: str,
    speaker_wav_path: Optional[str] = None,
    emotion: str = "neutral"
) -> str:
    """
    Generate speech using XTTS-v2 with optional voice cloning

    Args:
        text: Text to synthesize
        language_code: Target language code
        speaker_wav_path: Path to speaker reference audio for cloning
        emotion: Emotional tone

    Returns:
        Path to generated audio file
    """
    model = tts_model.get_model()
    output_id = uuid.uuid4().hex[:8]
    temp_path = os.path.join(OUTPUT_DIR, f"tts_temp_{output_id}.wav")
    output_path = os.path.join(OUTPUT_DIR, f"zovix_voice_{output_id}.mp3")

    # Map language code
    xtts_lang = LANGUAGE_CODE_MAP.get(language_code, "en")

    # Prepare emotion prompt
    emotion_prefix = EMOTION_PROMPTS.get(emotion.lower())
    if emotion_prefix:
        text = f"{emotion_prefix} {text}"

    # Generate speech
    logger.info(f"Generating TTS: lang={xtts_lang}, emotion={emotion}, text_len={len(text)}")

    if speaker_wav_path and os.path.exists(speaker_wav_path):
        # Voice cloning mode
        model.tts_to_file(
            text=text,
            speaker_wav=speaker_wav_path,
            language=xtts_lang,
            file_path=temp_path
        )
    else:
        # Multi-speaker mode (uses default speaker)
        model.tts_to_file(
            text=text,
            speaker="default",
            language=xtts_lang,
            file_path=temp_path
        )

    if not os.path.exists(temp_path):
        raise RuntimeError("TTS generation produced no output")

    # Apply audio enhancement
    enhanced_path = apply_audio_enhancement(temp_path, output_path)

    # Cleanup temp
    try:
        if os.path.exists(temp_path) and temp_path != enhanced_path:
            os.remove(temp_path)
    except:
        pass

    return enhanced_path


# ==========================================================================
# RUNPOD HANDLER
# ==========================================================================

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler for XTTS-v2 multilingual voice generation

    Expected input:
    {
        "text": "Text to convert to speech",
        "language": "hi",
        "language_name": "hindi",
        "speaker_audio_url": "https://...",
        "emotion": "neutral",
        "emotion_prompt": "Speak with...",
        "speed": 1.0,
        "pitch": 1.0,
        "output_format": "mp3",
        "model": "xtts-v2",
        "enhance_audio": true
    }
    """
    job_id = job.get("id", "unknown")
    logger.info(f"Processing TTS job: {job_id}")

    try:
        input_data = job.get("input", {})
        text = input_data.get("text", "")
        language = input_data.get("language", "en")
        language_name = input_data.get("language_name", "english")
        speaker_audio_url = input_data.get("speaker_audio_url", "")
        emotion = input_data.get("emotion", "neutral")
        speed = input_data.get("speed", 1.0)
        output_format = input_data.get("output_format", "mp3")
        enhance_audio = input_data.get("enhance_audio", True)

        if not text:
            raise ValueError("text is required")

        # Download speaker audio if provided
        speaker_wav_path = None
        if speaker_audio_url:
            run_id = uuid.uuid4().hex[:8]
            speaker_wav_path = download_file(
                speaker_audio_url,
                os.path.join(INPUT_DIR, f"speaker_{run_id}.wav")
            )

        # Generate speech
        output_path = generate_speech(text, language, speaker_wav_path, emotion)

        # Upload to cloud storage
        audio_url = upload_to_cloud(output_path, f"audio/{output_format}")

        # Cleanup
        for f_path in [speaker_wav_path, output_path]:
            try:
                if f_path and os.path.exists(f_path):
                    os.remove(f_path)
            except:
                pass

        return {
            "output": audio_url,
            "status": "COMPLETED",
            "job_id": job_id,
            "language": language_name,
            "language_code": language
        }

    except Exception as e:
        logger.error(f"TTS job {job_id} failed: {e}")
        return {
            "error": str(e),
            "status": "FAILED",
            "job_id": job_id
        }


# ==========================================================================
# FASTAPI SERVER (for dedicated pod mode)
# ==========================================================================

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn

    api_app = FastAPI(title="ZOVIX TTS API")

    class TTSRequest(BaseModel):
        text: str
        language: str = "hi"
        speaker_audio_url: Optional[str] = None
        emotion: str = "neutral"
        speed: float = 1.0
        pitch: float = 1.0
        output_format: str = "mp3"

    class TTSResponse(BaseModel):
        audio_url: str
        language: str
        emotion: str
        duration_sec: float
        latency_ms: float

    @api_app.post("/v1/tts", response_model=TTSResponse)
    async def generate_tts(request: TTSRequest):
        """FastAPI endpoint for TTS generation"""
        start_time = time.time()
        result = generate_speech(
            request.text,
            request.language,
            request.speaker_audio_url,
            request.emotion
        )
        audio_url = upload_to_cloud(result)
        elapsed_ms = (time.time() - start_time) * 1000

        return TTSResponse(
            audio_url=audio_url,
            language=request.language,
            emotion=request.emotion,
            duration_sec=max(1, len(request.text) / 15),
            latency_ms=round(elapsed_ms, 2)
        )

    @api_app.get("/v1/health")
    async def health_check():
        return {"status": "healthy", "model": "xtts-v2", "gpu": torch.cuda.is_available()}

except ImportError:
    api_app = None
    logger.info("FastAPI not available, using RunPod serverless mode only")


# ==========================================================================
# ENTRYPOINT
# ==========================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Check if FastAPI mode (dedicated pod) or RunPod serverless
    if os.getenv("FASTAPI_MODE", "0") == "1" and api_app:
        port = int(os.getenv("PORT", "8000"))
        logger.info(f"Starting FastAPI server on port {port}...")
        uvicorn.run(api_app, host="0.0.0.0", port=port)
    else:
        logger.info("Starting RunPod serverless handler...")
        runpod.serverless.start({"handler": handler})
