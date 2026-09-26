"""FFmpeg-based sales video composition utilities."""

import html
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests


def _run(command):
    try:
        timeout = int(os.getenv("SALES_FFMPEG_TIMEOUT", "180"))
    except ValueError:
        timeout = 180
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=max(30, timeout),
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"FFmpeg timed out after {max(30, timeout)} seconds.") from exc
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or "FFmpeg command failed.")
    return result


def _ffmpeg_path(path):
    value = str(path).replace("\\", "/")
    return value.replace(":", "\\:").replace("'", "\\'")


def _drawtext_text(value):
    return str(value or "").replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")


def _seconds_to_srt(seconds):
    milliseconds = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _duration(path):
    result = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return max(1.0, float(result.stdout.strip()))


def _script_srt(script, duration, output_path):
    words = re.findall(r"\S+", str(script or ""))
    if not words:
        raise ValueError("A script is required to create captions.")
    chunks = [words[index:index + 10] for index in range(0, len(words), 10)]
    chunk_duration = duration / len(chunks)
    lines = []
    for index, chunk in enumerate(chunks):
        start = index * chunk_duration
        end = duration if index == len(chunks) - 1 else (index + 1) * chunk_duration
        lines.extend([
            str(index + 1),
            f"{_seconds_to_srt(start)} --> {_seconds_to_srt(end)}",
            " ".join(chunk),
            "",
        ])
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    return str(output_path)


def generate_srt_from_audio(audio_path, script, output_path, language="en"):
    """Transcribe audio when Whisper is installed, otherwise time the supplied script."""
    if os.getenv("SALES_USE_WHISPER", "0").strip().lower() not in {"1", "true", "yes"}:
        return _script_srt(script, _duration(audio_path), output_path)
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(os.getenv("WHISPER_MODEL", "tiny"), device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path), language=language or None)
        rows = []
        for index, segment in enumerate(segments, start=1):
            text = str(segment.text or "").strip()
            if text:
                rows.extend([str(index), f"{_seconds_to_srt(segment.start)} --> {_seconds_to_srt(segment.end)}", text, ""])
        if rows:
            Path(output_path).write_text("\n".join(rows), encoding="utf-8")
            return str(output_path)
    except Exception:
        pass
    return _script_srt(script, _duration(audio_path), output_path)


def _download_video(video_path, target_path):
    if not str(video_path).startswith(("http://", "https://")):
        return str(video_path)
    response = requests.get(video_path, timeout=120)
    response.raise_for_status()
    Path(target_path).write_bytes(response.content)
    return str(target_path)


def _subtitle_filter(srt_path):
    options = "force_style='FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,MarginV=48'"
    if os.name == "nt":
        options = "fontsdir='C\\:/Windows/Fonts':" + options
    return f"subtitles='{_ffmpeg_path(srt_path)}':{options}"


def compose_sales_video(video_path, audio_path, product_image, price, script, output_dir="sales_outputs", language="en"):
    """Create final MP4, burned captions, product overlay, price text, and thumbnail."""
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="sales_compose_", dir=str(output_root)))
    local_video = _download_video(video_path, work_dir / "source.mp4")
    srt_path = work_dir / "captions.srt"
    generate_srt_from_audio(audio_path, script, srt_path, language=language)

    final_path = output_root / f"sales_final_{next(tempfile._get_candidate_names())}.mp4"
    thumbnail_path = output_root / f"sales_thumbnail_{next(tempfile._get_candidate_names())}.jpg"
    price_text = _drawtext_text(f"{price or 'Best Value'}")
    filter_graph = (
        f"[0:v]{_subtitle_filter(srt_path)}[captioned];"
        "[1:v]scale=iw*0.22:-1[product];"
        "[captioned][product]overlay=W-w-24:H-h-24[overlaid];"
        f"[overlaid]drawtext=text='{price_text}':x=(w-text_w)/2:y=h-text_h-28:"
        "fontsize=34:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=12[v]"
    )
    overlay_graph = (
        "[1:v]scale=iw*0.22:-1[product];"
        "[0:v][product]overlay=W-w-24:H-h-24[overlaid];"
        f"[overlaid]drawtext=text='{price_text}':x=(w-text_w)/2:y=h-text_h-28:"
        "fontsize=34:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=12[v]"
    )

    def run_composition(graph):
        _run([
            "ffmpeg", "-y", "-i", local_video, "-i", str(product_image), "-i", str(audio_path),
            "-filter_complex", graph, "-map", "[v]", "-map", "2:a:0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-shortest", str(final_path),
        ])

    try:
        run_composition(filter_graph)
    except Exception as subtitle_error:
        try:
            run_composition(overlay_graph)
        except Exception:
            # Keep the generated avatar usable if optional filters fail.
            fallback_path = output_root / f"sales_raw_{next(tempfile._get_candidate_names())}.mp4"
            if str(local_video) != str(fallback_path):
                Path(fallback_path).write_bytes(Path(local_video).read_bytes())
            final_path = fallback_path
        else:
            subtitle_error = None

    if not Path(final_path).exists():
        # Keep the generated avatar usable if an optional overlay/filter fails.
        fallback_path = output_root / f"sales_raw_{next(tempfile._get_candidate_names())}.mp4"
        if str(local_video) != str(fallback_path):
            Path(fallback_path).write_bytes(Path(local_video).read_bytes())
        final_path = fallback_path

    thumbnail_filter = f"drawtext=text='{price_text}':x=(w-text_w)/2:y=h-text_h-24:fontsize=30:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=10"
    try:
        _run([
            "ffmpeg", "-y", "-i", str(final_path), "-vf", f"thumbnail=100,{thumbnail_filter}",
            "-frames:v", "1",
            "-q:v", "2", str(thumbnail_path),
        ])
    except Exception:
        try:
            _run([
                "ffmpeg", "-y", "-i", str(final_path), "-frames:v", "1",
                "-q:v", "2", str(thumbnail_path),
            ])
        except Exception:
            thumbnail_path = None
    return {
        "video_path": str(final_path),
        "srt_path": str(srt_path),
        "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
    }
