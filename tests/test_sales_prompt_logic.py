from credits_engine import get_prompt_word_cost


def test_sales_prompt_cost_matches_face_video_logic():
    assert get_prompt_word_cost("AI Sales Video", "Standard", 50) == 15
    assert get_prompt_word_cost("AI Sales Video", "Standard", 85) == 20
    assert get_prompt_word_cost("AI Sales Video", "Standard", 120) == 30
    assert get_prompt_word_cost("AI Sales Video", "HD", 121) == 40
