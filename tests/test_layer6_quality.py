from layer6_master_engine import GHOST_QUALITY_PROFILES, _quality_filter_chain


def test_quality_filter_chain_upscales_interpolates_and_grades():
    filters = _quality_filter_chain(scale=4, target_fps=48)

    assert "hqdn3d=1.2:1.2:3:3" in filters
    assert "scale=trunc(iw*4/2)*2:trunc(ih*4/2)*2:flags=lanczos" in filters
    assert "minterpolate=fps=48" in filters
    assert "eq=contrast=1.08:saturation=1.08" in filters
    assert "colorbalance=" in filters
    assert "unsharp=" in filters


def test_quality_filter_chain_supports_lower_scale():
    filters = _quality_filter_chain(scale=2, target_fps=30)

    assert "scale=trunc(iw*2/2)*2:trunc(ih*2/2)*2:flags=lanczos" in filters
    assert "minterpolate=fps=30" in filters


def test_fast_standard_filter_avoids_expensive_temporal_interpolation():
    filters = _quality_filter_chain(
        scale=1,
        target_fps=30,
        output_size=(1280, 720),
        fast_render=True,
    )

    assert "scale=1280:720" in filters
    assert "fps=30" in filters
    assert "minterpolate" not in filters
    assert "hqdn3d" not in filters


def test_ghost_quality_profiles_only_include_standard_and_hd():
    assert GHOST_QUALITY_PROFILES == {
        "Standard": {
            "scale": 1, "size": (1280, 720), "fps": 30, "crf": 22,
            "preset": "ultrafast", "profile": "main", "level": "4.0",
        },
        "HD": {
            "scale": 2, "size": (1920, 1080), "fps": 48, "crf": 18,
            "preset": "fast", "profile": "high", "level": "4.2",
        },
    }


def test_hd_profile_has_higher_resolution_and_quality_than_standard():
    standard = GHOST_QUALITY_PROFILES["Standard"]
    hd = GHOST_QUALITY_PROFILES["HD"]

    assert standard["size"] < hd["size"]
    assert standard["fps"] < hd["fps"]
    assert standard["scale"] < hd["scale"]
    assert standard["crf"] > hd["crf"]
