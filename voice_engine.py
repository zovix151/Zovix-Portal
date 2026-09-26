"""Replicate-first voice generation with Edge-TTS fallback."""

import asyncio
import os
from pathlib import Path

import requests


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


def _replicate_token():
    token = os.getenv("REPLICATE_API_TOKEN", "") or os.getenv("REPLICATE_API_KEY", "")
    if not token:
        try:
            import streamlit as st
            token = st.secrets.get("REPLICATE_API_TOKEN", "") or st.secrets.get("REPLICATE_API_KEY", "")
        except Exception:
            token = ""
    return str(token).strip()


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
    voice_name = _LANGUAGE_VOICES.get(str(language), _LANGUAGE_VOICES["English"])
    tone_settings = {
        "Urgent": ("+12%", "+2Hz"),
        "Youthful": ("+8%", "+3Hz"),
        "Friendly": ("+2%", "+1Hz"),
        "Inspirational": ("+4%", "+2Hz"),
        "Luxury": ("-8%", "-1Hz"),
        "Professional": ("-2%", "0Hz"),
        "Humorous": ("+6%", "+3Hz"),
    }
    rate, pitch = tone_settings.get(str(tone or "Professional"), ("0%", "0Hz"))
    await edge_tts.Communicate(script, voice_name, rate=rate, pitch=pitch).save(output_path)


def generate_sales_voice(script, language, output_path, model_ref=None, tone=None):
    """Use Replicate first and Edge-TTS when Replicate is unavailable or fails."""
    try:
        return generate_voice_replicate(script, language, output_path, model_ref=model_ref, tone=tone)
    except Exception as replicate_error:
        try:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            asyncio.run(_save_edge_tts(script, language, str(target), tone=tone))
            if not target.exists() or target.stat().st_size < 512:
                raise RuntimeError("Edge-TTS returned an empty audio file.")
            return str(target)
        except Exception as edge_error:
            raise RuntimeError(
                f"Voice generation failed. Replicate: {replicate_error}; Edge-TTS: {edge_error}"
            ) from edge_error
