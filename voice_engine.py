"""Replicate-first voice generation with Edge-TTS fallback."""

import asyncio
import logging
import os
import threading
from pathlib import Path

import requests

logger = logging.getLogger("Zovix.SalesVoice")


_LANGUAGE_VOICES = {
    "English": "en-US-JennyNeural",
    "Hindi": "hi-IN-SwaraNeural",
    "Hinglish": "en-IN-NeerjaNeural",
    "Bhojpuri": "hi-IN-MadhurNeural",
    "French": "fr-FR-DeniseNeural",
    "Japanese": "ja-JP-NanamiNeural",
    "Spanish": "es-ES-ElviraNeural",
    "German": "de-DE-KatjaNeural",
}
_LANGUAGE_VOICE_FALLBACKS = {
    "English": ("en-US-JennyNeural", "en-US-AriaNeural"),
    "Hindi": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"),
    "Hinglish": ("en-IN-NeerjaNeural", "hi-IN-SwaraNeural"),
    "Bhojpuri": ("hi-IN-MadhurNeural", "hi-IN-SwaraNeural"),
    "French": ("fr-FR-DeniseNeural", "fr-FR-HenriNeural"),
    "Japanese": ("ja-JP-NanamiNeural", "ja-JP-KeitaNeural"),
    "Spanish": ("es-ES-ElviraNeural", "es-ES-AlvaroNeural"),
    "German": ("de-DE-KatjaNeural", "de-DE-ConradNeural"),
}


def _replicate_token():
    token = os.getenv("REPLICATE_API_TOKEN", "") or os.getenv("REPLICATE_API_KEY", "")
    if not token:
        try:
            import streamlit as st
            token = st.secrets.get("REPLICATE_API_TOKEN", "") or st.secrets.get("REPLICATE_API_KEY", "")
        except Exception:
            token = ""
    return str(token).strip()


def _elevenlabs_api_key():
    key = os.getenv("ELEVENLABS_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("ELEVENLABS_API_KEY", "")
        except Exception:
            key = ""
    return str(key or "").strip()


def generate_voice_elevenlabs(script, output_path, voice_id):
    """Generate MP3 speech with ElevenLabs using the selected sales voice."""
    if not str(script or "").strip():
        raise ValueError("Voice script is empty.")
    api_key = _elevenlabs_api_key()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured.")
    if not str(voice_id or "").strip():
        raise RuntimeError("No ElevenLabs voice is selected.")

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{str(voice_id).strip()}",
        headers={"xi-api-key": api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"},
        json={
            "text": str(script).strip(),
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
        },
        timeout=60,
    )
    if response.status_code != 200:
        detail = str(getattr(response, "text", "") or "").replace("\n", " ")[:240]
        raise RuntimeError(f"ElevenLabs returned HTTP {response.status_code}: {detail}")
    if len(response.content) < 2000:
        raise RuntimeError("ElevenLabs returned an empty or invalid audio file.")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    return str(target)


def _output_url(output):
    if isinstance(output, str) and output.startswith(("http://", "https://")):
        return output
    if isinstance(output, (list, tuple)):
        for item in output:
            found = _output_url(item)
            if found:
                return found
    for attr in ("url", "output", "audio"):
        value = getattr(output, attr, None)
        if value:
            found = _output_url(value)
            if found:
                return found
    if isinstance(output, dict):
        for key in ("audio", "output", "url", "audio_url"):
            found = _output_url(output.get(key))
            if found:
                return found
    return None


def generate_voice_replicate(script, language, output_path, model_ref=None, tone=None):
    """Generate speech through Replicate and save the returned audio locally."""
    if not str(script or "").strip():
        raise ValueError("Voice script is empty.")
    token = _replicate_token()
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not configured.")
    try:
        import replicate
    except ImportError as exc:
        raise RuntimeError("Install the Replicate package before generating voice.") from exc

    model_ref = str(model_ref or os.getenv("REPLICATE_VOICE_MODEL", "lucataco/xtts-v2")).strip()
    client = replicate.Client(api_token=token)
    payloads = []
    for language_value in (language, str(language).lower()):
        standard_payload = {"text": script, "language": language_value}
        if tone:
            tone_payload = dict(standard_payload)
            tone_payload["emotion"] = str(tone).lower()
            tone_payload["style"] = str(tone).lower()
            payloads.append(tone_payload)
        payloads.append(standard_payload)
    last_error = None
    for payload in payloads:
        try:
            output = client.run(model_ref, input=payload)
            audio_url = _output_url(output)
            if not audio_url:
                raise RuntimeError("Replicate returned no audio URL.")
            response = requests.get(audio_url, timeout=60)
            response.raise_for_status()
            audio_bytes = response.content
            if len(audio_bytes) < 512:
                raise RuntimeError("Replicate returned an empty audio file.")
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(audio_bytes)
            return str(target)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Replicate voice generation failed: {last_error}")


async def _save_edge_tts(script, language, output_path, tone=None):
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Install edge-tts to use the voice fallback.") from exc
    tone_settings = {
        "Urgent": ("+12%", "+2Hz"),
        "Youthful": ("+8%", "+3Hz"),
        "Friendly": ("+2%", "+1Hz"),
        "Inspirational": ("+4%", "+2Hz"),
        "Luxury": ("-8%", "-1Hz"),
        "Professional": ("-2%", "+0Hz"),
        "Humorous": ("+6%", "+3Hz"),
    }
    rate, pitch = tone_settings.get(str(tone or "Professional"), ("0%", "+0Hz"))
    language_name = str(language or "English")
    voices = _LANGUAGE_VOICE_FALLBACKS.get(
        language_name,
        (_LANGUAGE_VOICES.get(language_name, _LANGUAGE_VOICES["English"]),),
    )
    failures = []
    for voice_name in dict.fromkeys(voices):
        target = Path(output_path)
        target.unlink(missing_ok=True)
        try:
            await edge_tts.Communicate(script, voice_name, rate=rate, pitch=pitch).save(str(target))
            if target.exists() and target.stat().st_size >= 512:
                return str(target)
            raise RuntimeError(f"Edge-TTS voice {voice_name} returned an empty audio file.")
        except Exception as exc:
            failures.append(f"{voice_name}: {exc}")
            target.unlink(missing_ok=True)
    raise RuntimeError("All Edge-TTS voice attempts failed: " + "; ".join(failures))


def _run_coroutine_sync(coroutine):
    """Run an async TTS request safely, even when called on a thread with a live loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    result = []
    errors = []

    def run_in_worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result.append(loop.run_until_complete(coroutine))
        except Exception as exc:
            errors.append(exc)
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            asyncio.set_event_loop(None)

    worker = threading.Thread(target=run_in_worker, daemon=True)
    worker.start()
    worker.join()
    if errors:
        raise errors[0]
    if not result:
        raise RuntimeError("Edge-TTS fallback returned no result.")
    return result[0]


def generate_sales_voice(script, language, output_path, model_ref=None, tone=None, voice_id=None, progress=None):
    """Use ElevenLabs first and Edge-TTS if ElevenLabs fails."""
    try:
        if progress is not None:
            progress.update(label="Step 2/4: Generating voice with ElevenLabs...", state="running")
        result = generate_voice_elevenlabs(script, output_path, voice_id)
        if progress is not None:
            progress.update(label="Step 2/4: ElevenLabs voice ready", state="running")
        return result
    except Exception as elevenlabs_error:
        logger.warning("Sales ElevenLabs voice failed; trying Edge-TTS fallback: %s", elevenlabs_error)
        try:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            if progress is not None:
                progress.update(label="Step 2/4: ElevenLabs failed; generating voice with Edge-TTS fallback...", state="running")
            _run_coroutine_sync(_save_edge_tts(script, language, str(target), tone=tone))
            if not target.exists() or target.stat().st_size < 512:
                raise RuntimeError("Edge-TTS returned an empty audio file.")
            if progress is not None:
                progress.update(label="Step 2/4: Edge-TTS fallback voice ready", state="running")
            return str(target)
        except Exception as tts_error:
            raise RuntimeError(
                f"Voice generation failed. ElevenLabs: {elevenlabs_error}; Edge-TTS fallback: {tts_error}"
            ) from tts_error
