import json
import shutil
import subprocess
from pathlib import Path

import pytest

import layer6_master_engine


FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
pytestmark = pytest.mark.skipif(not FFMPEG or not FFPROBE, reason="FFmpeg tools are required")


def _run(command):
    subprocess.run(command, check=True, capture_output=True, text=True)


def _streams(path):
    result = subprocess.run(
        [
            FFPROBE, "-v", "error", "-show_entries",
            "stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["streams"]


def _write_test_video(path):
    _run([
        FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24:d=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
    ])


def test_voiceover_disabled_returns_silent_mp4(tmp_path, monkeypatch):
    source = tmp_path / "scene.mp4"
    _write_test_video(source)
    monkeypatch.setattr(
        layer6_master_engine,
        "_neural_upscale",
        lambda _src, target, **_kwargs: shutil.copy2(source, target) and "test",
    )
    monkeypatch.setattr(layer6_master_engine, "_ffmpeg", lambda: FFMPEG)

    output = Path(layer6_master_engine.finalize_browser_video(str(source), scale=2))
    try:
        assert output.is_file()
        assert [stream["codec_type"] for stream in _streams(output)] == ["video"]
    finally:
        output.unlink(missing_ok=True)


def test_quality_pass_locks_browser_video_dimensions_codec_and_fps(tmp_path):
    source = tmp_path / "scene.mp4"
    output = tmp_path / "browser-ready.mp4"
    _write_test_video(source)

    layer6_master_engine._neural_upscale(
        source,
        output,
        scale=1,
        output_size=(1280, 720),
        target_fps=30,
    )

    video_stream = next(stream for stream in _streams(output) if stream["codec_type"] == "video")
    assert video_stream["codec_name"] == "h264"
    assert (video_stream["width"], video_stream["height"]) == (1280, 720)
    assert video_stream["avg_frame_rate"] == "30/1"


def test_i2v_normalization_preserves_five_seconds_at_16_fps(tmp_path):
    source = tmp_path / "five-seconds-16fps.mp4"
    output = tmp_path / "five-seconds-24fps.mp4"
    _run([
        FFMPEG, "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=16:d=5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    import camera_motion_engine

    camera_motion_engine._normalize_i2v_video(source, output, 80, 5.0, 16.0)
    duration_result = subprocess.run(
        [
            FFPROBE, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert float(duration_result.stdout) == pytest.approx(5.0, abs=0.05)


def test_i2v_normalization_rejects_short_motion_instead_of_freeze_padding(tmp_path):
    source = tmp_path / "three-seconds.mp4"
    output = tmp_path / "should-not-exist.mp4"
    _run([
        FFMPEG, "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=24:d=3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    import camera_motion_engine

    with pytest.raises(RuntimeError, match="Refusing to pad with frozen frames"):
        camera_motion_engine._normalize_i2v_video(source, output, 72, 5.0, 24.0)

    assert not output.exists()


def test_voiceover_enabled_muxes_tts_audio_and_extends_video(tmp_path, monkeypatch):
    source = tmp_path / "scene.mp4"
    _write_test_video(source)
    monkeypatch.setattr(
        layer6_master_engine,
        "_neural_upscale",
        lambda _src, target, **_kwargs: shutil.copy2(source, target) and "test",
    )
    monkeypatch.setattr(layer6_master_engine, "_ffmpeg", lambda: FFMPEG)

    def write_test_voice(_text, output_path, _voice_id, model_id):
        assert model_id == "eleven_multilingual_v2"
        _run([
            FFMPEG, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:a", "libmp3lame", output_path,
        ])
        return output_path

    monkeypatch.setattr("voice_engine.generate_voice_elevenlabs", write_test_voice)
    output = Path(
        layer6_master_engine.finalize_browser_video(
            str(source), scale=2, voiceover_text="A short test narration."
        )
    )
    try:
        streams = _streams(output)
        assert any(stream["codec_type"] == "video" for stream in streams)
        assert any(
            stream["codec_type"] == "audio" and stream["codec_name"] == "aac"
            for stream in streams
        )
        duration_result = subprocess.run(
            [
                FFPROBE, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert float(duration_result.stdout) >= 1.9
    finally:
        output.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("quality", "size", "fps", "crf", "preset"),
    [
        ("Standard", "1280:720", "30", "22", "ultrafast"),
        ("HD", "1920:1080", "48", "18", "fast"),
    ],
)
def test_voiceover_mux_preserves_selected_quality_profile(
    tmp_path, monkeypatch, quality, size, fps, crf, preset
):
    source = tmp_path / "scene.mp4"
    _write_test_video(source)
    calls = {}
    monkeypatch.setattr(
        layer6_master_engine,
        "_neural_upscale",
        lambda _src, target, **kwargs: (
            calls.update(kwargs) or shutil.copy2(source, target) or "test"
        ),
    )

    def run_ffmpeg(command, **kwargs):
        calls["mux_command"] = command
        target = Path(command[-1])
        shutil.copy2(source, target)

        class Result:
            returncode = 0
            stderr = ""

        return Result()

    monkeypatch.setattr(layer6_master_engine.subprocess, "run", run_ffmpeg)
    monkeypatch.setattr(layer6_master_engine, "_ffmpeg", lambda: FFMPEG)

    def write_test_voice(_text, output_path, _voice_id, model_id):
        Path(output_path).write_bytes(b"voice" * 200)
        return output_path

    monkeypatch.setattr("voice_engine.generate_voice_elevenlabs", write_test_voice)
    output = Path(
        layer6_master_engine.finalize_browser_video(
            str(source),
            voiceover_text="A short test narration.",
            quality=quality,
        )
    )
    try:
        assert calls["scale"] == layer6_master_engine.GHOST_QUALITY_PROFILES[quality]["scale"]
        assert calls["output_size"] == tuple(
            int(dimension) for dimension in size.split(":")
        )
        assert calls["target_fps"] == int(fps)
        command = calls["mux_command"]
        assert command[command.index("-crf") + 1] == crf
        assert command[command.index("-preset") + 1] == preset
        assert command[command.index("-r") + 1] == fps
    finally:
        output.unlink(missing_ok=True)
