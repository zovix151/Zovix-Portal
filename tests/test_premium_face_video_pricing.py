from credits_engine import get_face_video_token_cost


def test_premium_face_video_uses_one_and_a_half_times_4k_word_band_rates():
    assert get_face_video_token_cost("Premium", 50) == 38
    assert get_face_video_token_cost("Premium", 85) == 48
    assert get_face_video_token_cost("Premium", 120) == 75
    assert get_face_video_token_cost("Premium", 121) is None
