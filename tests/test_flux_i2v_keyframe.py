from pathlib import Path

from PIL import Image

import flux_render_engine


def test_direct_i2v_keyframe_avoids_unneeded_8k_resize(tmp_path, monkeypatch):
    monkeypatch.setattr(flux_render_engine, "_OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(flux_render_engine, "_get_replicate_token", lambda: "test-token")
    monkeypatch.setattr(
        flux_render_engine,
        "_run_replicate_model",
        lambda *_args: {"output": "https://example.test/keyframe.png"},
    )
    monkeypatch.setattr(
        flux_render_engine,
        "_download_image",
        lambda *_args: Image.new("RGB", (1024, 576), color="blue"),
    )

    output = Path(
        flux_render_engine.generate_flux_keyframe({"flux_prompt": "A cinematic test scene."})
    )

    with Image.open(output) as image:
        assert image.size == flux_render_engine._I2V_KEYFRAME_SIZE
    assert output.stat().st_size < 5_000_000


def test_video_status_poll_interval_is_subsecond():
    import camera_motion_engine

    assert camera_motion_engine._I2V_POLL_INTERVAL_SECONDS < 1
    assert flux_render_engine._POLL_INTERVAL_SECONDS < 1
