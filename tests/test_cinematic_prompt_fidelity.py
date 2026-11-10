import io
from pathlib import Path

import pytest
from PIL import Image

import camera_motion_engine
import flux_render_engine
import layer6_master_engine
import spatial_director_engine


@pytest.mark.parametrize("with_reference", [False, True])
def test_original_details_reach_keyframe_and_motion(monkeypatch, with_reference):
    calls = {}
    script = "नीला कवच with tiny gold stars, a red left glove, no helmet."
    config = {
        "flux_prompt": "A warrior in a forest.",
        "character_action": "Walking Forward",
        "camera_motion": "Pan Left",
        "lighting_setup": "Natural Daylight",
        "atmosphere_fx": "None",
    }
    monkeypatch.setattr(
        spatial_director_engine, "generate_spatial_director_config",
        lambda value: config.copy(),
    )
    monkeypatch.setattr(
        flux_render_engine, "generate_flux_keyframe",
        lambda value: calls.update(keyframe=value.copy()) or "keyframe.png",
    )
    monkeypatch.setattr(
        camera_motion_engine, "apply_camera_motion",
        lambda *args, **kwargs: calls.update(motion=kwargs) or "motion.mp4",
    )
    monkeypatch.setattr(
        layer6_master_engine, "finalize_browser_video",
        lambda *args, **kwargs: "master.mp4",
    )

    reference = b"reference" if with_reference else None
    result = layer6_master_engine.run_zovix_ghost_engine(
        script, face_reference_bytes=reference, quality="HD",
    )

    assert result == "master.mp4"
    assert script in calls["keyframe"]["flux_prompt"]
    assert script in calls["motion"]["scene_prompt"]
    assert "Selected director controls override" in calls["motion"]["scene_prompt"]
    assert "armor" in calls["motion"]["scene_prompt"]
    assert calls["keyframe"].get("face_reference_bytes") == reference


@pytest.mark.parametrize("with_reference", [False, True])
def test_reference_model_is_used_only_with_face_lock(tmp_path, monkeypatch, with_reference):
    monkeypatch.setattr(flux_render_engine, "_OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(flux_render_engine, "_get_replicate_token", lambda: "test")
    monkeypatch.setattr(
        flux_render_engine, "_download_image",
        lambda *_args: Image.new("RGB", (1024, 576)),
    )
    calls = {}

    def run_model(model, model_input, _token):
        calls.update(model=model, model_input=model_input)
        return "https://example.test/image.png"

    monkeypatch.setattr(flux_render_engine, "_run_replicate_model", run_model)
    image = io.BytesIO()
    Image.new("RGB", (100, 100)).save(image, format="PNG")
    config = {"flux_prompt": "Warrior with a red cloak.", "aspect_ratio": "16:9"}
    if with_reference:
        config["face_reference_bytes"] = image.getvalue()
    output = Path(flux_render_engine.generate_flux_keyframe(config))

    assert output.is_file()
    if with_reference:
        assert calls["model"] == "black-forest-labs/flux-kontext-pro"
        assert calls["model_input"]["input_image"].startswith("data:image/jpeg;base64,")
        assert "image_prompt" not in calls["model_input"]
    else:
        assert calls["model"] == "black-forest-labs/flux-1.1-pro"
        assert "input_image" not in calls["model_input"]
    assert calls["model_input"]["prompt"] == config["flux_prompt"]
    assert calls["model_input"]["aspect_ratio"] == "16:9"


def test_reference_model_failure_does_not_drop_face_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(flux_render_engine, "_get_replicate_token", lambda: "test")
    image = io.BytesIO()
    Image.new("RGB", (100, 100)).save(image, format="PNG")
    models = []

    def fail(model, _input, _token):
        models.append(model)
        raise flux_render_engine._ReplicateSubmissionError(429, "Unavailable")

    monkeypatch.setattr(flux_render_engine, "_run_replicate_model", fail)
    with pytest.raises(RuntimeError, match="Face Lock requires the reference-image model"):
        flux_render_engine.generate_flux_keyframe({
            "flux_prompt": "A warrior", "face_reference_bytes": image.getvalue(),
        })
    assert models == ["black-forest-labs/flux-kontext-pro"]


def test_motion_payload_requests_consistent_character_details(monkeypatch):
    calls = {}
    monkeypatch.setattr(camera_motion_engine, "_get_replicate_token", lambda: "test")
    monkeypatch.setattr(camera_motion_engine, "_compact_image_data_uri", lambda *args, **kwargs: "image")

    def submit(_endpoint, _headers, payload):
        calls["prompt"] = payload["input"]["prompt"]
        raise RuntimeError("stop before network")

    monkeypatch.setattr(camera_motion_engine, "_post_i2v_prediction", submit)
    with pytest.raises(RuntimeError, match="stop before network"):
        camera_motion_engine._run_i2v_prediction(
            "keyframe.png", "Walk", "Pan Left", 5,
            scene_prompt="Original scene: blue armor, gold stars, no helmet.",
            model_ref="wan-video/wan-2.2-i2v-fast",
        )
    assert "blue armor, gold stars, no helmet" in calls["prompt"]
    assert "armor design" in calls["prompt"]
    assert "no identity changes" in calls["prompt"]
