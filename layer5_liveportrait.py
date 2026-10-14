"""Layer 5: dialogue audio, emotion-aware voice, and video lip-sync.

LivePortrait is an expression/portrait animation model; it does not consume
dialogue audio for phoneme-level lip sync. This layer therefore prefers a
video-capable Wav2Lip backend, with audio muxing as a safe final fallback.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

import logging
import os
import shutil
import subprocess
import uuid
logger = logging.getLogger("Zovix.Layer5")
ROOT = Path(__file__).resolve().parent

_EMOTION_TONES = {
    "angry": "Urgent", "sad": "Professional", "royal": "Luxury",
    "happy": "Friendly", "excited": "Inspirational", "neutral": "Professional",
    "serious": "Professional", "mysterious": "Luxury",
}

_LIVEPORTRAIT_MODEL = "charlesmccarthy/liveportrait"
_LIVEPORTRAIT_VERSION = "4d56e26a1ce02936e7c047b6ce9dc1a60fb7d97cc5a6a1f116a6a73af474cebf"


def animate_face_from_motion(
    source_image_path: str,
    driving_video_url: str,
    fallback_video_path: str,
    model_ref: str | None = None,
    model_version: str | None = None,
    timeout_seconds: int = 120,
) -> tuple[str, bool]:
    """Apply LivePortrait expression, blink, and head motion from the action clip."""
    try:
        from camera_motion_engine import (
            _compact_image_data_uri,
            _run_replicate_video_model,
        )

        image_data = _compact_image_data_uri(source_image_path, target_size=(1024, 576))
        output_path, _ = _run_replicate_video_model(
            model_ref or _LIVEPORTRAIT_MODEL,
            {
                "image": image_data,
                "video": driving_video_url,
                "flag_do_crop": True,
                "flag_pasteback": True,
            },
            label="liveportrait_face",
            timeout_seconds=timeout_seconds,
            version=model_version or _LIVEPORTRAIT_VERSION,
        )
        return output_path, True
    except Exception as exc:
        logger.warning("LivePortrait face animation failed; preserving motion video: %s", exc)
        return fallback_video_path, False


def _make_dialogue_audio(text: str, destination: Path, emotion: str, voice_emotion: str | None = None) -> Path:
    """Generate MP3 using the repository voice engine and its configured fallbacks."""
    try:
        from voice_engine import generate_sales_voice
        result = generate_sales_voice(
            text, os.getenv("LAYER5_TTS_LANGUAGE", "English"), str(destination),
            tone={
                "intense": "Urgent", "aggressive": "Urgent", "soft": "Professional",
                "dramatic": "Luxury",
            }.get(str(voice_emotion or "").strip().lower(),
                  _EMOTION_TONES.get(emotion.strip().lower(), "Professional")),
        )
        candidate = Path(result or destination)
        if candidate.is_file() and candidate.stat().st_size > 512:
            return candidate
    except Exception as exc:
        logger.warning("Configured TTS provider failed: %s", exc)
    raise RuntimeError(
        "Dialogue TTS failed. Configure ElevenLabs or install/configure edge-tts."
    )


def _run_wav2lip(video: Path, audio: Path, output: Path) -> bool:
    """Run local Wav2Lip against the full Layer 4 video, when configured."""
    repo = Path(os.getenv("WAV2LIP_REPO_PATH", str(ROOT / "Wav2Lip"))).expanduser()
    script = Path(os.getenv("WAV2LIP_SCRIPT_PATH", str(repo / "inference.py"))).expanduser()
    checkpoint = Path(os.getenv("WAV2LIP_CHECKPOINT_PATH", str(repo / "checkpoints" / "wav2lip_gan.pth"))).expanduser()
    if not script.is_file() or not checkpoint.is_file():
        return False
    command = [
        os.getenv("WAV2LIP_PYTHON_PATH", os.sys.executable), str(script),
        "--checkpoint_path", str(checkpoint), "--face", str(video),
        "--audio", str(audio), "--outfile", str(output),
    ]
    try:
        result = subprocess.run(command, cwd=str(repo), capture_output=True, text=True, timeout=1800)
        if result.returncode == 0 and output.is_file() and output.stat().st_size > 1000:
            return True
        logger.warning("Wav2Lip failed (rc=%s): %s", result.returncode, (result.stderr or "")[-1200:])
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Wav2Lip invocation failed: %s", exc)
    return False


def _mux_audio(video: Path, audio: Path, output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("No lip-sync backend succeeded and ffmpeg is unavailable for audio mux fallback.")
    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(output)],
        capture_output=True, text=True, timeout=900,
    )
    if result.returncode or not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(f"Audio mux fallback failed: {(result.stderr or '')[-1000:]}")


def apply_liveportrait_lip_sync(
    video_path: str,
    dialogue_text: str,
    emotion_state: str,
    voice_emotion: str | None = None,
) -> str:
    """Create dialogue audio and return the final lip-synced MP4 path.

    Layer 4's video is used as Wav2Lip's face video input. Emotion informs TTS
    tone; facial micro-expression control requires an expression-conditioned
    animation model and is not fabricated by this audio-sync stage.
    """
    source = Path(video_path).expanduser().resolve()
    text = str(dialogue_text or "").strip()
    emotion = str(emotion_state or "neutral").strip()
    if not source.is_file() or source.suffix.lower() != ".mp4":
        raise ValueError(f"Layer 4 video must be an existing .mp4 file: {video_path}")
    if not text:
        raise ValueError("dialogue_text cannot be empty.")

    out_dir = Path(os.getenv("LAYER5_OUTPUT_DIR", str(ROOT / "static" / "outputs"))).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"lip_synced_{uuid.uuid4().hex[:10]}"
    audio = out_dir / f"{stem}.mp3"
    output = out_dir / f"{stem}.mp4"
    candidate = out_dir / f"{stem}_w2l.mp4"
    try:
        audio = _make_dialogue_audio(text, audio, emotion, voice_emotion)
        if _run_wav2lip(source, audio, candidate):
            # Ensure dialogue audio is present and has a broadly compatible MP4 codec.
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg:
                remux = subprocess.run(
                    [ffmpeg, "-y", "-i", str(candidate), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
                     "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-shortest",
                     "-movflags", "+faststart", str(output)], capture_output=True, text=True, timeout=900,
                )
                if remux.returncode == 0 and output.is_file() and output.stat().st_size > 1000:
                    return str(output)
            shutil.move(str(candidate), str(output))
            return str(output)
        _mux_audio(source, audio, output)
        logger.warning("No lip-sync model available; returned video with dialogue audio muxed.")
        return str(output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    finally:
        audio.unlink(missing_ok=True)
        candidate.unlink(missing_ok=True)
