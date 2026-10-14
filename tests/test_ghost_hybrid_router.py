import camera_motion_engine
import numpy as np
from spatial_director_engine import (
    _CAMERA_MOTIONS,
    _CHARACTER_ACTION_OPTIONS,
    _CONFIG_SCHEMA,
)


def test_hybrid_router_maps_portrait_and_dynamic_actions():
    assert camera_motion_engine._select_hybrid_route("Hand Gestures / Talking") == (
        "portrait",
        5.0,
    )
    assert camera_motion_engine._select_hybrid_route("Facial Expressions") == (
        "portrait",
        5.0,
    )
    assert camera_motion_engine._select_hybrid_route("Sword Fight Action") == (
        "dynamic",
        5.0,
    )
    assert camera_motion_engine._select_hybrid_route("Running / Chasing") == (
        "dynamic",
        5.0,
    )
    assert "Orbit Left (360)" in camera_motion_engine._MOTION_TYPES
    assert "Orbit Right (360)" in camera_motion_engine._MOTION_TYPES
    assert "360-degree orbit" in camera_motion_engine._CAMERA_MOTION_PROMPTS["Orbit Left (360)"]


def test_all_reference_camera_moves_are_available_and_have_motion_prompts():
    assert camera_motion_engine._MOTION_TYPES == _CAMERA_MOTIONS
    assert _CONFIG_SCHEMA["properties"]["camera_motion"]["enum"] == list(
        _CAMERA_MOTIONS
    )
    assert set(camera_motion_engine._CAMERA_MOTION_PROMPTS) == set(_CAMERA_MOTIONS)
    assert len(_CAMERA_MOTIONS) == 26


def test_all_character_action_choices_are_prompted_and_routed():
    assert _CONFIG_SCHEMA["properties"]["character_action"]["enum"][:16] == list(
        _CHARACTER_ACTION_OPTIONS
    )
    assert set(_CHARACTER_ACTION_OPTIONS[1:]).issubset(
        camera_motion_engine._ACTION_MOTION_PROMPTS
    )
    assert camera_motion_engine._select_hybrid_route(
        "None (Camera Motion Only)"
    )[0] == "camera"
    assert camera_motion_engine._select_hybrid_route(
        "Standing Still / Subtle Breathing"
    )[0] == "dynamic"
    assert camera_motion_engine._select_hybrid_route(
        "Hand Gestures & Expressive Dialogue"
    )[0] == "portrait"


def test_talking_action_uses_liveportrait_over_fast_i2v(monkeypatch):
    calls = {}

    def run_i2v(_keyframe, _prompt, _motion, duration, _scene, **kwargs):
        calls["duration"] = duration
        calls.update(kwargs)
        return "driving.mp4", "https://replicate.example/driving.mp4"

    def animate(_image, driving_url, fallback_path, **kwargs):
        calls["driving_url"] = driving_url
        calls["fallback"] = fallback_path
        calls["portrait_options"] = kwargs
        return "portrait.mp4", True

    monkeypatch.setattr(camera_motion_engine, "_run_i2v_prediction", run_i2v)
    monkeypatch.setenv("ZOVIX_GHOST_FAST_I2V_MODEL", "lightricks/ltx-video-0.9.7")
    monkeypatch.setenv("ZOVIX_GHOST_FAST_I2V_VERSION", "fast-version")
    monkeypatch.setattr(
        "layer5_liveportrait.animate_face_from_motion",
        animate,
    )

    result = camera_motion_engine.apply_camera_motion(
        "keyframe.png",
        None,
        "Pan Left",
        character_action="Hand Gestures / Talking",
    )

    assert result == "portrait.mp4"
    assert calls["duration"] == 5.0
    assert calls["model_ref"] == "lightricks/ltx-video-0.9.7"
    assert calls["model_version"] == "fast-version"
    assert calls["timeout_seconds"] <= 600
    assert calls["driving_url"] == "https://replicate.example/driving.mp4"


def test_dynamic_action_uses_wan_22_default_route(monkeypatch):
    calls = {}
    monkeypatch.delenv("ZOVIX_GHOST_FAST_I2V_MODEL", raising=False)
    monkeypatch.delenv("ZOVIX_GHOST_FAST_I2V_VERSION", raising=False)

    def run_i2v(_keyframe, _prompt, _motion, duration, _scene, **kwargs):
        calls["duration"] = duration
        calls.update(kwargs)
        return "action.mp4", "https://replicate.example/action.mp4"

    monkeypatch.setattr(camera_motion_engine, "_run_i2v_prediction", run_i2v)
    result = camera_motion_engine.apply_camera_motion(
        "keyframe.png",
        None,
        "Tracking (Forward)",
        duration_seconds=5.0,
        character_action="Sword Fight Action",
    )

    assert result == "action.mp4"
    assert calls["duration"] == 5.0
    assert calls["model_ref"] == "wan-video/wan-2.2-i2v-fast"
    assert calls["wan_resolution"] == "480p"


def test_wan_22_input_defaults_to_fast_480p_and_supports_hd(monkeypatch):
    monkeypatch.delenv("ZOVIX_GHOST_WAN_RESOLUTION", raising=False)

    fast_model_input = camera_motion_engine._build_i2v_input(
        "wan-video/wan-2.2-i2v-fast",
        "data:image/jpeg;base64,test",
        "A cinematic character runs forward.",
        121,
    )
    hd_model_input = camera_motion_engine._build_i2v_input(
        "wan-video/wan-2.2-i2v-fast",
        "data:image/jpeg;base64,test",
        "A cinematic character runs forward.",
        121,
        wan_resolution="720p",
    )

    assert fast_model_input == {
        "prompt": "A cinematic character runs forward.",
        "image": "data:image/jpeg;base64,test",
        "resolution": "480p",
    }
    assert hd_model_input == {
        "prompt": "A cinematic character runs forward.",
        "image": "data:image/jpeg;base64,test",
        "resolution": "720p",
    }
    assert camera_motion_engine._I2V_MODEL == "wan-video/wan-2.2-i2v-fast"


def test_action_route_waits_for_replicate_longer_and_does_not_hide_failure(monkeypatch):
    monkeypatch.delenv("ZOVIX_GHOST_ROUTER_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("ZOVIX_GHOST_FAST_I2V_MODEL", raising=False)
    calls = {}

    def fail_i2v(*_args, **kwargs):
        calls.update(kwargs)
        raise TimeoutError("Replicate inference timed out")

    def forbidden_local_fallback(*_args, **_kwargs):
        raise AssertionError("Action failure must not silently return a pan/zoom clip.")

    monkeypatch.setattr(camera_motion_engine, "_run_i2v_prediction", fail_i2v)
    monkeypatch.setattr(
        camera_motion_engine,
        "_render_2d_camera_motion",
        forbidden_local_fallback,
    )

    try:
        camera_motion_engine.apply_camera_motion(
            "keyframe.png",
            None,
            "Orbit Left (360)",
            character_action="Sword Fight Action",
        )
    except RuntimeError as exc:
        assert "No pan/zoom-only fallback was substituted" in str(exc)
    else:
        raise AssertionError("Expected provider failure to be surfaced to the caller.")

    assert calls["timeout_seconds"] == 300


def test_isolated_temporal_frame_outlier_is_replaced_by_neighbor_blend():
    previous = np.full((72, 128, 3), 40, dtype=np.uint8)
    corrupted = np.full((72, 128, 3), 240, dtype=np.uint8)
    following = np.full((72, 128, 3), 42, dtype=np.uint8)

    filtered = camera_motion_engine._replace_temporal_outlier(
        previous, corrupted, following
    )

    assert np.all(filtered == 41)


def test_temporal_filter_preserves_legitimate_continuous_motion():
    previous = np.full((72, 128, 3), 30, dtype=np.uint8)
    current = np.full((72, 128, 3), 80, dtype=np.uint8)
    following = np.full((72, 128, 3), 130, dtype=np.uint8)

    filtered = camera_motion_engine._replace_temporal_outlier(
        previous, current, following
    )

    assert np.array_equal(filtered, current)
