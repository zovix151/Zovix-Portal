import pytest

import blueprint_generation


class FakeOpenAIResponse:
    status_code = 200

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"prompt":"Precise technical plan with legible labels",'
                            '"negative_prompt":"extra rooms"}'
                        )
                    }
                }
            ]
        }


@pytest.mark.parametrize(
    ("render_mode", "expected_ratio"),
    [("2D Technical Plan", "4:3"), ("3D Concept View", "16:9")],
)
def test_gpt4o_prompt_flows_to_replicate_with_original_brief(
    monkeypatch,
    render_mode,
    expected_ratio,
):
    openai_calls = {}
    replicate_calls = {}

    def fake_openai_post(url, *, headers, json, timeout):
        openai_calls.update(url=url, headers=headers, payload=json, timeout=timeout)
        return FakeOpenAIResponse()

    def fake_replicate(prompt, aspect_ratio, negative_prompt, quality):
        replicate_calls.update(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
            quality=quality,
        )
        return "blueprint.png"

    monkeypatch.setattr(blueprint_generation.requests, "post", fake_openai_post)
    result = blueprint_generation.generate_blueprint_image_with_gpt4o(
        prompt="2-bedroom home, kitchen beside the living room, 800 sq ft",
        blueprint_type="floor_plan",
        style="Modern",
        render_mode=render_mode,
        quality="HD",
        template_context="Garden-facing entrance",
        api_key="test-key",
        replicate_generator=fake_replicate,
    )

    assert result == "blueprint.png"
    assert openai_calls["payload"]["model"] == "gpt-4o"
    assert openai_calls["payload"]["response_format"] == {"type": "json_object"}
    assert openai_calls["headers"]["Authorization"] == "Bearer test-key"
    assert "2-bedroom home, kitchen beside the living room, 800 sq ft" in replicate_calls["prompt"]
    assert "Garden-facing entrance" in replicate_calls["prompt"]
    assert replicate_calls["aspect_ratio"] == expected_ratio
    assert replicate_calls["quality"] == "HD"
    assert "extra rooms" in replicate_calls["negative_prompt"]


def test_blueprint_generation_does_not_fake_success_when_replicate_fails(monkeypatch):
    monkeypatch.setattr(
        blueprint_generation.requests,
        "post",
        lambda *_args, **_kwargs: FakeOpenAIResponse(),
    )

    with pytest.raises(RuntimeError, match="Replicate did not return"):
        blueprint_generation.generate_blueprint_image_with_gpt4o(
            prompt="A small workshop with one workbench",
            blueprint_type="floor_plan",
            style="Industrial",
            render_mode="2D Technical Plan",
            quality="Standard",
            template_context="",
            api_key="test-key",
            replicate_generator=lambda *_args: None,
        )
