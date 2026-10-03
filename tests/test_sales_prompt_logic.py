from credits_engine import get_face_video_token_cost, get_prompt_word_cost
from deepseek_engine import _build_sales_script_prompt


def test_sales_video_cost_is_fixed_by_quality():
    assert get_prompt_word_cost("AI Sales Video", "Standard", 1) == 70
    assert get_prompt_word_cost("AI Sales Video", "Standard", 120) == 70
    assert get_prompt_word_cost("AI Sales Video", "HD", 1) == 85
    assert get_prompt_word_cost("AI Sales Video", "4K", 120) == 100


def test_face_video_word_pricing_is_unchanged():
    assert get_face_video_token_cost("Standard", 50) == 15
    assert get_face_video_token_cost("Standard", 85) == 20
    assert get_face_video_token_cost("HD", 121) == 40


def test_sales_scripts_use_casual_friend_to_friend_voice_and_light_fillers():
    prompt = _build_sales_script_prompt(
        "Wireless earbuds", "Rs 999", "Electronics", "Hinglish",
        "clear and friendly", "", "",
    )

    assert "talking to a friend" in prompt
    assert "avoid formal or corporate wording" in prompt
    assert "one or two light, language-appropriate fillers" in prompt
    assert "do not force repeated stutters" in prompt
    assert "do not claim that the presenter bought, owns, used" in prompt


def test_sales_scripts_only_use_personal_experience_when_provided():
    prompt = _build_sales_script_prompt(
        "Wireless earbuds", "Rs 999", "Electronics", "Hindi",
        "clear and friendly", "", "Maine inhe 3 mahine daily commute par use kiya.",
    )

    assert "Maine inhe 3 mahine daily commute par use kiya." in prompt
    assert "using only those exact facts" in prompt
    assert "do not invent a personal/family story" in prompt


def test_sales_scripts_keep_product_category_out_of_spoken_copy():
    prompt = _build_sales_script_prompt(
        "Wireless earbuds", "Rs 999", "Electronics", "Hindi",
        "clear, modern, and benefit-focused", "", "",
    )

    assert "Category: Electronics" not in prompt
    assert "electronics" not in prompt.lower()
    assert "internal writing guidance only" in prompt
    assert "Never announce, explain, or name the product category" in prompt
