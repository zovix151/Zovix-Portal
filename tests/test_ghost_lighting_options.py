import pytest

from spatial_director_engine import (
    _ATMOSPHERE_EFFECTS,
    _CHARACTER_ACTIONS,
    _CONFIG_SCHEMA,
    _LIGHTING_SETUPS,
    _validate_config,
)


EXPECTED_LIGHTING_SETUPS = (
    "Natural Daylight",
    "Soft Overcast Daylight",
    "Harsh Midday Sun",
    "Dappled Forest Sunlight",
    "Window Light",
    "Sunrise",
    "Sunset",
    "Volumetric Golden Hour",
    "Blue Hour Twilight",
    "Moonlight",
    "Candlelight",
    "Firelight",
    "Practical Tungsten Lamps",
    "Fluorescent Office Light",
    "Sodium Vapor Streetlights",
    "Neon Sign Glow",
    "Dramatic Backlight Silhouette",
    "Dramatic Rim Light",
    "Edge Light",
    "Top Light",
    "Underlighting",
    "Rembrandt Lighting",
    "Butterfly / Paramount Lighting",
    "Loop Lighting",
    "Split Lighting",
    "Three-Point Studio Lighting",
    "High-Key Studio Lighting",
    "Low-Key Studio Lighting",
    "Softbox Lighting",
    "Beauty Dish Lighting",
    "Ring Light",
    "Clamshell Beauty Lighting",
    "Hard Spotlight",
    "Fresnel Spotlight",
    "Stage Follow Spot",
    "Gobo Pattern Lighting",
    "Projector Light",
    "Light Shafts / God Rays",
    "Volumetric God Rays",
    "Foggy Backlight",
    "Silhouette Lighting",
    "Cool Blue Hour",
    "Warm Tungsten Glow",
    "Teal and Orange Cinematic",
    "Monochromatic Red",
    "Monochromatic Blue",
    "RGB Color Wash",
    "Two-Tone Color Lighting",
    "Gradient Background Lighting",
    "Cyberpunk Neon",
    "Chiaroscuro / Shadow Drama",
    "Soft Studio Key Light",
    "Fire & Candlelight Glow",
    "Lightning / Strobe Flashes",
    "Bioluminescent Glow",
    "Laser Beams",
    "TV / Screen Flicker",
    "Candle Flicker",
    "Underwater Caustic Light",
    "Ember Glow",
    "Horror Uplight",
    "Silvery Moonlit Haze",
    "Soft Beauty Lighting",
    "Cinematic Naturalistic Lighting",
)

EXPECTED_ATMOSPHERE_EFFECTS = (
    "None",
    "Rain & Storm",
    "Heavy Fog & Mist",
    "Flying Embers & Fire Sparks",
    "Dust Motes & Light Leaks",
    "Blizzard & Snowstorm",
    "Crimson Dust Storm",
    "Thick Smoke & Haze",
    "Ash Fall",
    "Underwater Bubble Flow",
    "Bioluminescent Spores",
    "Heat Haze Distortion",
)


@pytest.mark.parametrize("lighting", EXPECTED_LIGHTING_SETUPS)
def test_lighting_choices_are_in_director_schema_and_validated(lighting):
    config = {
        "flux_prompt": "A cinematic scene.",
        "camera_motion": "Pan Left",
        "lighting_setup": lighting,
        "atmosphere_fx": "None",
        "character_action": "None (Camera Motion Only)",
        "emotion_state": "Calm",
        "audio_dialogue": "",
        "voice_emotion": "Soft",
    }

    assert _LIGHTING_SETUPS == EXPECTED_LIGHTING_SETUPS
    assert _CONFIG_SCHEMA["properties"]["lighting_setup"]["enum"] == list(
        EXPECTED_LIGHTING_SETUPS
    )
    assert _validate_config(config, "A cinematic scene.")["lighting_setup"] == lighting


@pytest.mark.parametrize("atmosphere", EXPECTED_ATMOSPHERE_EFFECTS)
def test_atmosphere_choices_are_in_director_schema_and_validated(atmosphere):
    config = {
        "flux_prompt": "A cinematic scene.",
        "camera_motion": "Pan Left",
        "lighting_setup": "Volumetric Golden Hour",
        "atmosphere_fx": atmosphere,
        "character_action": "None (Camera Motion Only)",
        "emotion_state": "Calm",
        "audio_dialogue": "",
        "voice_emotion": "Soft",
    }

    assert _ATMOSPHERE_EFFECTS == EXPECTED_ATMOSPHERE_EFFECTS
    assert _CONFIG_SCHEMA["properties"]["atmosphere_fx"]["enum"] == list(
        EXPECTED_ATMOSPHERE_EFFECTS
    )
    assert _validate_config(config, "A cinematic scene.")["atmosphere_fx"] == atmosphere


def test_character_action_is_required_and_uses_complete_allowed_list():
    assert _CONFIG_SCHEMA["properties"]["character_action"]["enum"] == list(
        _CHARACTER_ACTIONS
    )
    assert "Reaching Out Hand" in _CHARACTER_ACTIONS
