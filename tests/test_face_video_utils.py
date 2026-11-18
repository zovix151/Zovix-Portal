import pytest

from face_video_utils import (
    default_elevenlabs_voice_id_for_gender,
    face_video_dimensions,
)


@pytest.mark.parametrize(
    ("gender", "expected_voice_id"),
    [
        ("male", "pNInz6obpgDQ5IdwJg7p"),
        ("female", "21m00Tcm4TlvDq8ikWAM"),
        ("Woman", "21m00Tcm4TlvDq8ikWAM"),
    ],
)
def test_default_elevenlabs_voice_id_matches_gender(gender, expected_voice_id):
    assert default_elevenlabs_voice_id_for_gender(gender) == expected_voice_id


@pytest.mark.parametrize(
    ("ratio", "expected_dimensions"),
    [
        ("9:16", (288, 512)),
        ("16:9", (512, 288)),
        ("1:1", (512, 512)),
    ],
)
def test_face_video_dimensions_preserve_requested_ratio(ratio, expected_dimensions):
    assert face_video_dimensions(512, ratio) == expected_dimensions


def test_face_video_dimensions_reject_unsupported_ratio():
    with pytest.raises(ValueError, match="Unsupported face video aspect ratio"):
        face_video_dimensions(512, "4:3")
