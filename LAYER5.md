# Layer 5: dialogue and lip sync

Call the engine with the Layer 4 MP4 path and Layer 1 dialogue/emotion:

```python
from layer5_liveportrait import apply_liveportrait_lip_sync

final_path = apply_liveportrait_lip_sync(fx_video_path, audio_dialogue, emotion_state)
```

The engine uses the existing `voice_engine.generate_sales_voice` chain (ElevenLabs, then Edge-TTS) to create a temporary MP3. Set `LAYER5_TTS_LANGUAGE` if the dialogue is not English. Emotion names such as `Angry`, `Sad`, and `Royal` are mapped to the existing voice tone presets.

For actual mouth synchronization, configure local Wav2Lip with `WAV2LIP_REPO_PATH`, `WAV2LIP_CHECKPOINT_PATH`, and optionally `WAV2LIP_PYTHON_PATH` / `WAV2LIP_SCRIPT_PATH`. The default paths target this repository's `Wav2Lip` folder. Final MP4 files are written under `static/outputs` (override with `LAYER5_OUTPUT_DIR`). If Wav2Lip is not ready, the engine muxes dialogue audio over the source video and logs that synchronization was unavailable.

LivePortrait's official inference path animates a portrait from a driving video; it does not accept dialogue audio for phoneme-level lip sync. This layer therefore uses Wav2Lip for audio-driven mouth motion. Brows, blinks, and head nods are not individually driven by the current interface; those require a separate expression-conditioned motion input/model. Audio muxing is only a playback fallback and does not animate the face.
