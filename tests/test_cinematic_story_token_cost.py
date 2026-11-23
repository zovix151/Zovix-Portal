import pytest

from credits_engine import get_cinematic_story_token_cost, get_prompt_word_cost


@pytest.mark.parametrize(
    ("character_count", "expected_cost"),
    [
        (0, 0),
        (1, 10),
        (250, 10),
        (251, 15),
        (600, 15),
        (601, 20),
        (1200, 20),
        (1201, 40),
        (2000, 40),
    ],
)
def test_story_engine_cost_by_character_count(character_count, expected_cost):
    assert get_cinematic_story_token_cost(character_count) == expected_cost
    assert get_prompt_word_cost(
        "Cinematic Engine",
        "HD",
        character_count=character_count,
    ) == expected_cost


def test_deepseek_blueprint_remains_a_separate_four_credit_charge():
    assert get_prompt_word_cost("DeepSeek AI Blueprint") == 4
