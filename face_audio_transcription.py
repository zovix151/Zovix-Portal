import os
from functools import lru_cache


@lru_cache(maxsize=2)
def _load_model(model_name):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Local voice transcription is unavailable. Install dependencies from requirements.txt."
        ) from exc

    return WhisperModel(model_name, device="cpu", compute_type="int8")


def transcribe_audio_word_count(audio_path):
    model_name = os.getenv("FACE_STUDIO_ASR_MODEL", "small").strip() or "small"
    model = _load_model(model_name)
    segments, _ = model.transcribe(str(audio_path), beam_size=3, vad_filter=True)
    transcript = " ".join(
        str(segment.text or "").strip()
        for segment in segments
        if str(segment.text or "").strip()
    )
    if not transcript:
        raise ValueError("No speech could be transcribed from the recorded voice.")
    return len(transcript.split())
