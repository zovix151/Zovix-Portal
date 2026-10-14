"""Layer 6 and sequential master orchestration for ZOVIX Ghost Engine."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid
logger = logging.getLogger("Zovix.Layer6")
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "static" / "outputs"
GHOST_QUALITY_PROFILES = {
    "Standard": {
        "scale": 1, "size": (1280, 720), "fps": 30, "crf": 22,
        "preset": "ultrafast", "profile": "main", "level": "4.0",
    },
    "HD": {
        "scale": 2, "size": (1920, 1080), "fps": 48, "crf": 18,
        "preset": "fast", "profile": "high", "level": "4.2",
    },
}


def _ffmpeg() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("ffmpeg is required for Layer 6 upscaling and audio mastering.")
    return binary


def _video_info(path: Path) -> tuple[float, float]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 24.0, 3.0
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate:format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    lines = (result.stdout or "").splitlines()
    try:
        fraction = lines[0].split("/")
        fps = float(fraction[0]) / float(fraction[1]) if len(fraction) == 2 else float(fraction[0])
        duration = float(lines[-1])
        if fps > 0 and duration > 0:
            return fps, duration
    except (ValueError, ZeroDivisionError, IndexError):
        pass
    return 24.0, 3.0


def _quality_filter_chain(
    scale: int,
    target_fps: float,
    output_size: tuple[int, int] | None = None,
    fast_render: bool = False,
) -> str:
    if output_size:
        resize_filter = (
            f"scale={output_size[0]}:{output_size[1]}:flags=lanczos"
        )
    else:
        scale = 4 if int(scale) >= 4 else 2
        resize_filter = (
            f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2:flags=lanczos"
        )
    if fast_render:
        return (
            f"{resize_filter},fps={target_fps:g},"
            "eq=contrast=1.05:saturation=1.05:brightness=0.003"
        )
    return (
        "hqdn3d=1.2:1.2:3:3,"
        f"{resize_filter},"
        f"minterpolate=fps={target_fps:g}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
        "eq=contrast=1.08:saturation=1.08:brightness=0.005:gamma=0.98,"
        "colorbalance=rs=0.018:gs=0.004:bs=-0.018:rh=-0.008:gh=0:bh=0.012,"
        "unsharp=5:5:0.4:3:3:0.12"
    )


def _neural_upscale(
    video: Path,
    silent_output: Path,
    scale: int = 4,
    output_size: tuple[int, int] | None = None,
    target_fps: float | None = None,
    crf: int = 18,
    fast_render: bool = False,
    encoder_preset: str | None = None,
    codec_profile: str = "high",
    codec_level: str | None = None,
) -> str:
    """Upscale, interpolate, and grade video using Real-ESRGAN or FFmpeg fallback."""
    ffmpeg = _ffmpeg()
    binary = shutil.which(os.getenv("LAYER6_REALESRGAN_BIN", "realesrgan-ncnn-vulkan"))
    model = os.getenv("LAYER6_REALESRGAN_MODEL", "realesrgan-x4plus")
    scale = int(scale)
    if scale not in {1, 2, 4}:
        raise ValueError("Quality scale must be 1, 2, or 4.")
    source_fps, _ = _video_info(video)
    if target_fps is None:
        try:
            target_fps = float(os.getenv("LAYER6_OUTPUT_FPS", "48"))
        except ValueError:
            logger.warning("Invalid LAYER6_OUTPUT_FPS; using 48 FPS.")
            target_fps = 48.0
    target_fps = min(60.0, max(24.0, target_fps))
    quality_filters = _quality_filter_chain(
        scale, target_fps, output_size, fast_render=fast_render
    )
    preset = encoder_preset or ("ultrafast" if fast_render else "fast")
    codec_options = ["-profile:v", codec_profile]
    if codec_level:
        codec_options += ["-level:v", codec_level]
    if binary and scale > 1:
        with tempfile.TemporaryDirectory(prefix="zovix_esrgan_") as temp:
            temp_path = Path(temp)
            input_frames, output_frames = temp_path / "in", temp_path / "out"
            input_frames.mkdir()
            output_frames.mkdir()
            extract = subprocess.run(
                [ffmpeg, "-y", "-i", str(video), "-vsync", "0", str(input_frames / "%08d.png")],
                capture_output=True, text=True, timeout=1800,
            )
            frame_paths = sorted(input_frames.glob("*.png"))
            if extract.returncode == 0 and frame_paths:
                try:
                    for index, frame in enumerate(frame_paths, start=1):
                        target = output_frames / frame.name
                        result = subprocess.run(
                            [binary, "-i", str(frame), "-o", str(target), "-n", model,
                             "-s", str(scale), "-f", "png"],
                            capture_output=True, text=True, timeout=180,
                        )
                        if result.returncode or not target.is_file():
                            raise RuntimeError((result.stderr or "Real-ESRGAN frame inference failed")[-800:])
                        if index % 100 == 0:
                            logger.info("Real-ESRGAN upscaled %d frames", index)
                    encode = subprocess.run(
                        [ffmpeg, "-y", "-framerate", f"{source_fps:.6f}",
                         "-i", str(output_frames / "%08d.png"), "-vf",
                         _quality_filter_chain(1, target_fps, output_size).split(",", 1)[1],
                         "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                         *codec_options,
                         "-pix_fmt", "yuv420p", "-r", f"{target_fps:g}",
                         "-fps_mode", "cfr", "-movflags", "+faststart", "-an",
                         str(silent_output)],
                        capture_output=True, text=True, timeout=1800,
                    )
                    if encode.returncode == 0 and silent_output.is_file() and silent_output.stat().st_size > 1000:
                        return "Real-ESRGAN"
                except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
                    logger.warning("Real-ESRGAN failed; using FFmpeg enhancement: %s", exc)
                    silent_output.unlink(missing_ok=True)

    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(video), "-vf", quality_filters,
         "-c:v", "libx264", "-preset", preset,
         "-crf", str(crf), *codec_options, "-pix_fmt", "yuv420p",
         "-r", f"{target_fps:g}", "-fps_mode", "cfr",
         "-movflags", "+faststart", "-an", str(silent_output)],
        capture_output=True, text=True, timeout=1800,
    )
    if result.returncode or not silent_output.is_file() or silent_output.stat().st_size < 1000:
        raise RuntimeError(f"Video upscale failed: {(result.stderr or '')[-1200:]}")
    logger.warning(
        "Real-ESRGAN unavailable; applied %sx Lanczos upscale, %g FPS motion interpolation, "
        "and cinematic color grading.",
        scale,
        target_fps,
    )
    return "Lanczos fallback"


def _master_audio(video: Path, silent_video: Path, output: Path, ambience_path: str | None = None) -> None:
    ffmpeg = _ffmpeg()
    fps, duration = _video_info(video)
    del fps
    provided = Path(ambience_path).expanduser() if ambience_path else None
    if provided and not provided.is_file():
        raise FileNotFoundError(f"Ambient sound file does not exist: {provided}")
    command = [ffmpeg, "-y", "-i", str(silent_video), "-i", str(video)]
    if provided:
        command += ["-stream_loop", "-1", "-i", str(provided)]
        ambiance_index = "2:a"
        ambiance_filter = "volume=0.13,highpass=f=80,lowpass=f=9000,afade=t=in:st=0:d=1"
    else:
        command += ["-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.025:duration={duration:.3f}:sample_rate=48000"]
        ambiance_index = "2:a"
        ambiance_filter = "lowpass=f=850,highpass=f=100,volume=0.75,afade=t=in:st=0:d=1"
    graph = (
        "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        "aecho=0.8:0.75:35:0.12,volume=1.0[dialogue];"
        f"[{ambiance_index}]{ambiance_filter}[ambience];"
        "[dialogue][ambience]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,"
        "alimiter=limit=0.95,loudnorm=I=-16:TP=-1.5:LRA=11[mix]"
    )
    command += ["-filter_complex", graph, "-map", "0:v:0", "-map", "[mix]", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    if result.returncode or not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(f"Spatial audio mastering failed: {(result.stderr or '')[-1200:]}")


def finalize_ghost_video(video_path: str, ambience_path: str | None = None, scale: int = 4) -> str:
    """Layer 6: upscale/sharpen frames and master dialogue with cinematic ambience."""
    source = Path(video_path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".mp4":
        raise ValueError(f"Layer 6 input must be an existing MP4: {video_path}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"final_master_cinematic_{uuid.uuid4().hex[:8]}.mp4"
    silent = OUTPUT_DIR / f".layer6_video_{uuid.uuid4().hex[:8]}.mp4"
    try:
        upscaler = _neural_upscale(source, silent, scale)
        _master_audio(source, silent, output, ambience_path or os.getenv("LAYER6_AMBIENCE_PATH"))
        logger.info("Layer 6 complete; upscaler=%s output=%s", upscaler, output)
        return str(output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    finally:
        silent.unlink(missing_ok=True)


def finalize_motion_video(video_path: str, scale: int = 4) -> str:
    """Upscale the direct image-to-video result and return a playable MP4."""
    source = Path(video_path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".mp4":
        raise ValueError(f"Motion input must be an existing MP4: {video_path}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"ghost_motion_master_{uuid.uuid4().hex[:10]}.mp4"
    try:
        upscaler = _neural_upscale(source, output, scale)
        logger.info("Direct motion master complete; upscaler=%s output=%s", upscaler, output)
        return str(output)
    except Exception:
        output.unlink(missing_ok=True)
        raise


def finalize_browser_video(
    video_path: str,
    scale: int = 4,
    voiceover_text: str | None = None,
    voice_id: str | None = None,
    quality: str | None = None,
    voice_model: str | None = None,
) -> str:
    """Upscale, grade, and package a silent or narrated MP4 for browser playback."""
    source = Path(video_path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".mp4":
        raise ValueError(f"Browser video input must be an existing MP4: {video_path}")
    narration = str(voiceover_text or "").strip()
    if quality is not None:
        if quality not in GHOST_QUALITY_PROFILES:
            raise ValueError(
                f"Unsupported Ghost Engine quality {quality!r}. "
                f"Choose one of: {', '.join(GHOST_QUALITY_PROFILES)}."
            )
        profile = GHOST_QUALITY_PROFILES[quality]
        scale = profile["scale"]
        output_size = profile["size"]
        target_fps = profile["fps"]
        crf = profile["crf"]
        encoder_preset = profile["preset"]
        codec_profile = profile["profile"]
        codec_level = profile["level"]
    else:
        output_size = None
        target_fps = None
        crf = 18
        encoder_preset = "fast"
        codec_profile = "high"
        codec_level = None
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"browser_ready_{uuid.uuid4().hex[:10]}.mp4"
    enhanced = OUTPUT_DIR / f".quality_pass_{uuid.uuid4().hex[:10]}.mp4"
    voice_file = OUTPUT_DIR / f".voiceover_{uuid.uuid4().hex[:10]}.mp3"
    try:
        upscaler = _neural_upscale(
            source,
            enhanced,
            scale=scale,
            output_size=output_size,
            target_fps=target_fps,
            crf=crf,
            fast_render=quality == "Standard",
            encoder_preset=encoder_preset,
            codec_profile=codec_profile,
            codec_level=codec_level,
        )
        if not narration:
            shutil.copy2(enhanced, output)
            logger.info("Silent browser-ready master created with %s: %s", upscaler, output)
            return str(output)

        from voice_engine import generate_voice_elevenlabs

        configured_voice_id = (
            voice_id
            or os.getenv("GHOST_ENGINE_ELEVENLABS_VOICE_ID")
            or "21m00Tcm4TlvDq8ikWAM"
        )
        generate_voice_elevenlabs(
            narration,
            str(voice_file),
            configured_voice_id,
            model_id=voice_model or "eleven_multilingual_v2",
        )
        if not voice_file.is_file() or voice_file.stat().st_size < 512:
            raise RuntimeError("ElevenLabs did not produce a usable Ghost Engine voiceover.")
        result = subprocess.run(
            [
                _ffmpeg(), "-y", "-i", str(enhanced), "-i", str(voice_file),
                "-filter_complex", "[0:v]tpad=stop_mode=clone:stop=-1[v]",
                "-map", "[v]", "-map", "1:a:0", "-shortest",
                "-c:v", "libx264",
                "-preset", encoder_preset,
                "-crf", str(crf),
                "-profile:v", codec_profile,
                *(["-level:v", codec_level] if codec_level else []),
                *(["-r", str(target_fps), "-fps_mode", "cfr"] if target_fps else []),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", str(output),
            ],
            capture_output=True,
            text=True,
            timeout=900,
        )
        if result.returncode or not output.is_file() or output.stat().st_size < 1000:
            raise RuntimeError(
                f"Could not prepare a browser-compatible MP4: {(result.stderr or '')[-1200:]}"
            )
        logger.info("Voiceover browser-ready master created with %s: %s", upscaler, output)
        return str(output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    finally:
        enhanced.unlink(missing_ok=True)
        voice_file.unlink(missing_ok=True)


def run_zovix_ghost_engine(
    user_script: str,
    config_overrides: dict | None = None,
    progress_callback=None,
    ambience_path: str | None = None,
    upscale_scale: int = 4,
    voiceover_text: str | None = None,
    voice_id: str | None = None,
    quality: str | None = None,
    voice_model: str | None = None,
) -> str:
    """Run the direct GPT-4o → Flux Pro → image-to-video workflow."""
    if not isinstance(user_script, str) or not user_script.strip():
        raise ValueError("user_script must be a non-empty string.")
    started = time.perf_counter()
    stage = "validation"
    artifacts: list[str] = []
    stages = ["GPT-4o prompt optimization", "Flux Pro keyframe", "Direct image-to-video"]

    def report(index: int, state: str) -> None:
        if progress_callback:
            progress_callback({
                "stage": stages[index], "step": index + 1, "total": len(stages),
                "progress": index / len(stages) if state == "running" else (index + 1) / len(stages),
                "state": state, "elapsed_seconds": time.perf_counter() - started,
            })

    try:
        logger.info("Ghost Engine pipeline started.")
        stage_started = time.perf_counter()
        stage = "Layer 1: spatial direction"
        report(0, "running")
        from spatial_director_engine import (
            _ATMOSPHERE_EFFECTS,
            _CAMERA_MOTIONS,
            _CHARACTER_ACTIONS,
            _LIGHTING_SETUPS,
            apply_character_action_to_config,
            generate_spatial_director_config,
        )
        config = generate_spatial_director_config(user_script)
        if config_overrides:
            allowed = {
                "camera_motion": set(_CAMERA_MOTIONS),
                "lighting_setup": set(_LIGHTING_SETUPS),
                "atmosphere_fx": set(_ATMOSPHERE_EFFECTS),
                "character_action": set(_CHARACTER_ACTIONS),
            }
            for key, value in config_overrides.items():
                if key not in allowed or value not in allowed[key]:
                    raise ValueError(f"Invalid Layer 1 override: {key}={value!r}")
                config[key] = value
        character_action = (config_overrides or {}).get(
            "character_action", config["character_action"]
        )
        camera_motion = (config_overrides or {}).get("camera_motion", config["camera_motion"])
        lighting_setup = (config_overrides or {}).get("lighting_setup", config["lighting_setup"])
        atmosphere_fx = (config_overrides or {}).get("atmosphere_fx", config["atmosphere_fx"])
        config["flux_prompt"] = (
            f"{config['flux_prompt'].rstrip()} Director controls: {camera_motion} camera movement, "
            f"{lighting_setup} lighting, {atmosphere_fx} atmosphere. "
            "Compose with consistent subject identity, cinematic framing, and clean frame edges."
        )
        apply_character_action_to_config(config, character_action)
        logger.info(
            "Ghost Engine stage completed: %s in %.2fs.",
            stage,
            time.perf_counter() - stage_started,
        )
        report(0, "complete")

        stage_started = time.perf_counter()
        stage = "Flux Pro keyframe"
        report(1, "running")
        from flux_render_engine import generate_flux_keyframe
        keyframe = generate_flux_keyframe(config)
        artifacts.append(keyframe)
        logger.info(
            "Ghost Engine stage completed: %s in %.2fs.",
            stage,
            time.perf_counter() - stage_started,
        )
        report(1, "complete")

        stage_started = time.perf_counter()
        stage = "Direct image-to-video"
        report(2, "running")
        from camera_motion_engine import apply_camera_motion
        try:
            requested_duration = float(os.getenv("ZOVIX_GHOST_I2V_DURATION_SECONDS", "5"))
        except ValueError:
            requested_duration = 5.0
        duration = min(5.0, max(2.0, requested_duration))
        final_path = apply_camera_motion(
            keyframe,
            None,
            camera_motion,
            duration_seconds=duration,
            character_action=character_action,
            scene_prompt=config["flux_prompt"],
            quality=quality,
        )
        artifacts.append(final_path)
        logger.info(
            "Ghost Engine stage completed: %s in %.2fs.",
            stage,
            time.perf_counter() - stage_started,
        )
        stage_started = time.perf_counter()
        stage = "Browser-ready video mastering"
        final_path = finalize_browser_video(
            final_path,
            scale=upscale_scale,
            voiceover_text=voiceover_text,
            voice_id=voice_id,
            quality=quality,
            voice_model=voice_model,
        )
        artifacts.append(final_path)
        logger.info(
            "Ghost Engine stage completed: %s in %.2fs.",
            stage,
            time.perf_counter() - stage_started,
        )
        report(2, "complete")
        elapsed = time.perf_counter() - started
        logger.info("Ghost Engine pipeline completed in %.2fs: %s", elapsed, final_path)
        return final_path
    except Exception as exc:
        elapsed = time.perf_counter() - started
        logger.exception("Ghost Engine failed at %s after %.2fs", stage, elapsed)
        raise RuntimeError(f"Zovix Ghost Engine failed at {stage} after {elapsed:.1f}s: {exc}") from exc
    finally:
        for artifact in artifacts:
            try:
                path = Path(artifact)
                # Preserve generated outputs for review/debugging; clean only no artifacts here.
                if not path.exists():
                    logger.debug("Pipeline artifact already removed: %s", path)
            except (TypeError, OSError):
                pass
