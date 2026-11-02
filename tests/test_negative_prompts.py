from urllib.parse import parse_qs, urlparse

import engine
from negative_prompts import (
    DRAW_DEFAULT_NEGATIVE_PROMPT,
    WORKSHOP_DEFAULT_NEGATIVE_PROMPT,
    combine_negative_prompts,
)


def test_user_negative_constraints_are_combined_with_defaults_once():
    combined = combine_negative_prompts(
        "blurry or out of focus image, extra hands, my custom constraint",
        DRAW_DEFAULT_NEGATIVE_PROMPT,
    )

    assert "blurry or out of focus image" in combined
    assert combined.count("blurry or out of focus image") == 1
    assert "extra hands" in combined
    assert "my custom constraint" in combined


def test_workshop_has_backend_negative_constraints_without_user_input():
    combined = combine_negative_prompts("", WORKSHOP_DEFAULT_NEGATIVE_PROMPT)

    assert "missing requested elements" in combined
    assert "gibberish lettering" in combined
    assert "watermarks" in combined


def test_draw_prompt_always_includes_quality_constraints():
    enhanced = engine._enhance_prompt("a fox in a forest", "digital")

    assert "malformed hands or faces" in enhanced
    assert "unrequested text" in enhanced
    assert "watermarks" in enhanced


def test_pollinations_draw_request_always_sends_default_negative_prompt(monkeypatch):
    class FakeResponse:
        status_code = 200
        content = b"image" * 1200

    requests_seen = []

    def fake_get(url, **_kwargs):
        requests_seen.append(url)
        return FakeResponse()

    monkeypatch.setattr(engine.requests, "get", fake_get)

    assert engine._draw_pollinations("a fox in a forest", "digital", (512, 512))

    query = parse_qs(urlparse(requests_seen[0]).query)
    assert query["nologo"] == ["true"]
    assert "gibberish lettering" in query["negative"][0]


def test_stability_draw_request_uses_default_negative_prompt(monkeypatch):
    class FakeResponse:
        status_code = 200
        content = b"image" * 2500

    captured = {}

    def fake_post(_url, *, headers, files, timeout):
        captured.update(headers=headers, files=files, timeout=timeout)
        return FakeResponse()

    monkeypatch.setenv("STABILITY_API_KEY", "test-token")
    monkeypatch.setattr(engine, "get_system_secret", lambda _key: None)
    monkeypatch.setattr(engine.requests, "post", fake_post)

    assert engine._draw_stability("a fox in a forest", "digital", (512, 512))

    assert "negative_prompt" in captured["files"]
    assert "malformed hands or faces" in captured["files"]["negative_prompt"][1]
