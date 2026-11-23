from types import SimpleNamespace

import face_audio_transcription


class FakeWhisperModel:
    def __init__(self, transcript):
        self.transcript = transcript

    def transcribe(self, audio_path, **kwargs):
        return iter([SimpleNamespace(text=self.transcript)]), None


def test_transcribe_audio_word_count_counts_transcribed_words(monkeypatch):
    monkeypatch.setattr(
        face_audio_transcription,
        "_load_model",
        lambda model_name: FakeWhisperModel("spoken words " * 60),
    )

    assert face_audio_transcription.transcribe_audio_word_count("recording.wav") == 120


def test_transcribe_audio_word_count_reports_over_limit_count(monkeypatch):
    monkeypatch.setattr(
        face_audio_transcription,
        "_load_model",
        lambda model_name: FakeWhisperModel("spoken words " * 61),
    )

    assert face_audio_transcription.transcribe_audio_word_count("recording.wav") == 122
