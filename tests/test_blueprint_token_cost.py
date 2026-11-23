from credits_engine import get_prompt_word_cost


def test_blueprint_token_cost_matches_selected_quality():
    assert get_prompt_word_cost("Blueprints", "Standard") == 7
    assert get_prompt_word_cost("Blueprints", "HD") == 10
    assert get_prompt_word_cost("DeepSeek AI Blueprint") == 4
