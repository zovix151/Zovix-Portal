import pytest

from credits_engine import get_live_emotion_token_cost, get_prompt_word_cost


@pytest.mark.parametrize(
    ("character_count", "expected_cost"),
    [
        (0, 0),
        (1, 5),
        (250, 5),
        (251, 7),
        (600, 7),
        (601, 12),
        (1200, 12),
        (1201, 18),
        (1800, 18),
        (1801, 24),
    ],
)
def test_live_emotion_cost_by_character_count(character_count, expected_cost):
    assert get_live_emotion_token_cost(character_count) == expected_cost
    assert get_prompt_word_cost(
        "Live Emotion",
        character_count=character_count,
    ) == expected_cost
