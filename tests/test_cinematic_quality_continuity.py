import base64
import io
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

import camera_motion_engine as motion
import layer5_liveportrait
import layer6_master_engine


def test_hd_action_uses_1080p_canvas_and_720p_provider(monkeypatch):
    calls = {}
    monkeypatch.delenv("ZOVIX_GHOST_FAST_I2V_MODEL", raising=False)
    monkeypatch.setattr(
        motion, "_run_i2v_prediction",
        lambda *args, **kwargs: (calls.update(kwargs) or "motion.mp4", "https://example.test/video"),
    )
    assert motion.apply_camera_motion(
        "keyframe.png", None, "Pan Left", character_action="Walking Forward",
        quality="HD", aspect_ratio="9:16",
    ) == "motion.mp4"
    assert calls["wan_resolution"] == "720p"
    assert calls["output_size"] == (1080, 1920)


@pytest.mark.parametrize(
    ("canvas", "expected_reference"),
    [((1920, 1080), (1280, 720)), ((1080, 1920), (720, 1280)), ((1080, 1080), (1280, 1280))],
)
def test_hd_reference_and_environment_prompt(monkeypatch, canvas, expected_reference):
    calls = {}
    monkeypatch.setattr(motion, "_get_replicate_token", lambda: "test")
    monkeypatch.setattr(
        motion, "_compact_image_data_uri",
        lambda path, target_size: calls.update(size=target_size) or "image",
    )

    def capture_payload(_endpoint, _headers, payload):
        calls["input"] = payload["input"]
        raise RuntimeError("stop before network")

    monkeypatch.setattr(motion, "_post_i2v_prediction", capture_payload)
    with pytest.raises(RuntimeError, match="stop before network"):
        motion._run_i2v_prediction(
            "keyframe.png", "Walk", "Pan Left", 5, "A forest",
            model_ref="wan-video/wan-2.2-i2v-fast", wan_resolution="720p",
            output_size=canvas,
        )
    assert calls["size"] == expected_reference
    assert calls["input"]["resolution"] == "720p"
    assert "background objects and structures geometrically stable" in calls["input"]["prompt"]
    assert "retain any environmental motion explicitly requested" in calls["input"]["prompt"]


def test_complex_reference_stays_under_inline_limit(tmp_path):
    rng = np.random.default_rng(42)
    image = rng.integers(0, 256, (720, 1280, 3), dtype=np.uint8)
    path = tmp_path / "noise.png"
    assert cv2.imwrite(str(path), image)
    data_uri = motion._compact_image_data_uri(str(path), (1280, 720))
    data = base64.b64decode(data_uri.split(",", 1)[1])
    assert len(data) <= 240 * 1024
    with Image.open(io.BytesIO(data)) as decoded:
        assert decoded.width >= 768
        assert abs(decoded.width / decoded.height - 16 / 9) < 0.01


def test_liveportrait_respects_portrait_canvas(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        motion, "_compact_image_data_uri",
        lambda path, target_size: calls.update(reference=target_size) or "image",
    )
    monkeypatch.setattr(
        motion, "_run_replicate_video_model",
        lambda *args, **kwargs: (calls.update(options=kwargs) or "portrait.mp4", "url"),
    )
    result = layer5_liveportrait.animate_face_from_motion(
        "image.png", "https://example.test/video", "fallback.mp4", output_size=(1080, 1920),
    )
    assert result == ("portrait.mp4", True)
    assert calls["reference"] == (576, 1024)
    assert calls["options"]["output_size"] == (1080, 1920)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg is required")
@pytest.mark.parametrize("camera", ["Pan Left", "Tilt Up", "Dolly Out", "Roll Clockwise"])
def test_camera_motion_has_no_reflected_or_empty_edges(tmp_path, monkeypatch, camera):
    monkeypatch.setattr(motion, "_OUTPUT_ROOT", tmp_path)
    image_path = tmp_path / "white.png"
    assert cv2.imwrite(str(image_path), np.full((90, 160, 3), 255, dtype=np.uint8))
    output = Path(motion._render_2d_camera_motion(str(image_path), camera, 1.0, (160, 90)))
    capture = cv2.VideoCapture(str(output))
    frames = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    assert len(frames) == 24
    assert min(int(frame.min()) for frame in frames) >= 240


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg is required")
def test_hd_normalization_crops_without_upscaling(tmp_path):
    source, output = tmp_path / "input.mp4", tmp_path / "output.mp4"
    subprocess.run(
        [shutil.which("ffmpeg"), "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:r=24:d=1",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)],
        check=True, capture_output=True,
    )
    motion._normalize_i2v_video(
        source, output, 24, 1, 24, output_size=(1920, 1080), preserve_source_size=True,
    )
    capture = cv2.VideoCapture(str(output))
    assert (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))) == (320, 180)
    capture.release()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg is required")
def test_hd_camera_clip_is_mastered_to_1080p(tmp_path, monkeypatch):
    monkeypatch.setattr(motion, "_OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(layer6_master_engine, "OUTPUT_DIR", tmp_path)
    monkeypatch.setenv("LAYER6_REALESRGAN_BIN", "zovix-unavailable-upscaler")
    image_path = tmp_path / "keyframe.png"
    assert cv2.imwrite(str(image_path), np.full((720, 1280, 3), 180, dtype=np.uint8))

    clip = motion.apply_camera_motion(
        str(image_path), None, "Pan Left", duration_seconds=0.25, quality="HD",
    )
    master = layer6_master_engine.finalize_browser_video(clip, quality="HD")

    capture = cv2.VideoCapture(master)
    assert capture.isOpened()
    assert (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))) == (1920, 1080)
    assert capture.get(cv2.CAP_PROP_FPS) == pytest.approx(30)
    ok, frame = capture.read()
    capture.release()
    assert ok
    assert frame.min() > 150
