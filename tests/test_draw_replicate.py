import engine


class FakeResponse:
    def __init__(self, status_code, payload=None, content=b""):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content

    def json(self):
        return self._payload


def test_replicate_draw_uses_supported_input_and_returns_image(monkeypatch):
    monkeypatch.setenv("REPLICATE_API_KEY", "test-token")
    monkeypatch.setattr(engine, "get_system_secret", lambda _key: None)
    monkeypatch.setattr(engine.time, "sleep", lambda _seconds: None)
    calls = {}

    def fake_post(url, *, json, headers, timeout):
        calls.update(url=url, payload=json, headers=headers)
        return FakeResponse(201, {"urls": {"get": "https://api.replicate.com/predictions/123"}})

    def fake_get(url, **_kwargs):
        if url.endswith("/predictions/123"):
            return FakeResponse(200, {"status": "succeeded", "output": ["https://images.example/result.png"]})
        return FakeResponse(200, content=b"image" * 1200)

    monkeypatch.setattr(engine.requests, "post", fake_post)
    monkeypatch.setattr(engine.requests, "get", fake_get)

    result = engine._draw_replicate("a mountain at sunrise", "realistic", (1024, 768), timeout=10)

    assert result == b"image" * 1200
    assert calls["url"] == "https://api.replicate.com/v1/models/black-forest-labs/flux-dev/predictions"
    assert calls["headers"]["Authorization"] == "Bearer test-token"
    inputs = calls["payload"]["input"]
    assert inputs["aspect_ratio"] == "4:3"
    assert inputs["output_format"] == "png"
    assert "width" not in inputs
    assert "height" not in inputs
    assert "logos" in inputs["prompt"]
    assert "watermarks" in inputs["prompt"]


def test_local_draw_fallback_does_not_add_branding(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    text_calls = []
    original_text = engine.ImageDraw.ImageDraw.text

    def record_text(draw, *args, **kwargs):
        text_calls.append(args)
        return original_text(draw, *args, **kwargs)

    monkeypatch.setattr(engine.ImageDraw.ImageDraw, "text", record_text)

    output_path = engine._draw_generative_fallback("blue sky", "digital", (256, 256))

    assert output_path
    assert not text_calls
