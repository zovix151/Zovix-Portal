from pathlib import Path

import pytest

import voice_engine


class _VoiceListResponse:
    status_code = 200
    text = ""

    @staticmethod
    def json():
        return {
            "voices": [
                {"voice_id": "voice-1", "name": "My Voice"},
                {"voice_id": "voice-2", "name": "Studio Voice"},
                {"name": "Incomplete voice"},
                None,
            ]
        }


def test_list_elevenlabs_voices_returns_named_account_voices(monkeypatch):
    calls = {}
    monkeypatch.setattr(voice_engine, "_elevenlabs_api_key", lambda: "test-key")

    def get(url, **kwargs):
        calls["url"] = url
        calls.update(kwargs)
        return _VoiceListResponse()

    monkeypatch.setattr(voice_engine.requests, "get", get)

    assert voice_engine.list_elevenlabs_voices() == [
        {"voice_id": "voice-1", "name": "My Voice"},
        {"voice_id": "voice-2", "name": "Studio Voice"},
    ]
    assert calls["url"] == "https://api.elevenlabs.io/v1/voices"
    assert calls["headers"]["xi-api-key"] == "test-key"


def test_generate_elevenlabs_uses_selected_voice_and_model(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr(voice_engine, "_elevenlabs_api_key", lambda: "test-key")

    class Response:
        status_code = 200
        content = b"a" * 2500

    def post(url, **kwargs):
        calls["url"] = url
        calls.update(kwargs)
        return Response()

    monkeypatch.setattr(voice_engine.requests, "post", post)
    output_path = tmp_path / "voice.mp3"

    result = voice_engine.generate_voice_elevenlabs(
        "Hello there.",
        output_path,
        "voice-2",
        model_id="eleven_flash_v2_5",
    )

    assert result == str(output_path)
    assert Path(result).read_bytes() == b"a" * 2500
    assert calls["url"].endswith("/voice-2")
    assert calls["json"]["model_id"] == "eleven_flash_v2_5"


def test_generate_elevenlabs_rejects_unknown_model(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_engine, "_elevenlabs_api_key", lambda: "test-key")

    with pytest.raises(ValueError, match="Unsupported ElevenLabs model"):
        voice_engine.generate_voice_elevenlabs(
            "Hello there.",
            tmp_path / "voice.mp3",
            "voice-2",
            model_id="not-a-model",
        )
