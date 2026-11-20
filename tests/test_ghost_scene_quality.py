from ghost_engine_studio import (
    _AUTO_SCENE_SETTING,
    _build_director_overrides,
)


def test_auto_scene_controls_allow_director_to_choose_lighting_and_atmosphere():
    assert _build_director_overrides(
        "Pan Left",
        _AUTO_SCENE_SETTING,
        _AUTO_SCENE_SETTING,
        "Standing Still / Subtle Breathing",
    ) == {
        "camera_motion": "Pan Left",
        "character_action": "Standing Still / Subtle Breathing",
    }


def test_explicit_lighting_and_atmosphere_override_scene_matching():
    assert _build_director_overrides(
        "Pan Left",
        "Warm Sunset",
        "Rain & Storm",
        "Standing Still / Subtle Breathing",
    ) == {
        "camera_motion": "Pan Left",
        "lighting_setup": "Warm Sunset",
        "atmosphere_fx": "Rain & Storm",
        "character_action": "Standing Still / Subtle Breathing",
    }
