import credits_engine
from credits_engine import get_prompt_word_cost


def test_ghost_engine_token_cost_matches_selected_quality(monkeypatch):
    assert credits_engine.GHOST_ENGINE_TOKEN_COST == 25
    assert get_prompt_word_cost("Ghost Engine", "Standard") == 25
    assert get_prompt_word_cost("Ghost Engine", "HD") == 40

    monkeypatch.setattr(credits_engine, "GHOST_ENGINE_TOKEN_COST", 7)
    assert get_prompt_word_cost("Ghost Engine", "Standard") == 7


def test_cinematic_engine_token_cost_is_fixed_by_quality_and_not_duration():
    assert get_prompt_word_cost("Cinematic Engine", "Standard", duration_choice="Quick Format Shorts") == 25
    assert get_prompt_word_cost("Cinematic Engine", "HD", duration_choice="1 minute") == 40
