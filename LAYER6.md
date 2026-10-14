# Layer 6: neural upscale, spatial audio, master orchestration

Run the complete six-layer pipeline:

```python
from layer6_master_engine import run_zovix_ghost_engine

master_mp4 = run_zovix_ghost_engine(user_script)
```

The orchestrator calls the repository's Layer 1–5 modules in sequence and returns a unique `static/outputs/final_master_cinematic_*.mp4` path. It estimates narration length from the dialogue and gives Layer 3 a matching clip duration (up to three minutes), instead of always generating the old three-second camera move. It logs stage failures and total elapsed time. Intermediate renders are retained for inspection.

Layer 6 uses `realesrgan-ncnn-vulkan` when available (override its executable with `LAYER6_REALESRGAN_BIN`; model with `LAYER6_REALESRGAN_MODEL`). It processes frames at 4x by default. If the executable is unavailable or fails, FFmpeg uses Lanczos scaling, mild temporal denoising, motion-compensated interpolation, and a mild unsharp filter. The fallback improves apparent crispness and reduces isolated temporal noise, but does not synthesize neural texture. Upscaling cannot recover authentic skin pores or fabric detail absent from the source.

The hosted Wan/Replicate endpoint returns an encoded video rather than latent tensors. Ghost Engine requests a five-second clip by default. Standard quality uses Wan 480p input and a fast FFmpeg export, then packages at 720p/30 FPS; HD uses 720p generation and full temporal interpolation. Set `ZOVIX_GHOST_WAN_RESOLUTION=720p` to override the fast default. Before mastering, Layer 3 checks decoded frames for isolated outliers (only when adjacent frames agree) and replaces those frames with a neighbor blend. It preserves the source frame rate during decoding, then converts to 24 FPS; this avoids speeding up 16 FPS provider clips. Clips shorter than five seconds are rejected instead of padded with a frozen frame. The final quality profile then locks its selected dimensions and constant frame rate and exports H.264/yuv420p MP4 with fast-start metadata for browser and Streamlit playback. Hosted-model queue and inference times depend on Replicate availability, so low-resolution generation and faster local encoding reduce work but cannot guarantee completion within one minute.

Ghost Engine offers two export tiers in both silent and voiceover renders: Standard exports 1280x720 at 30 FPS (CRF 22, ultrafast); HD exports 1920x1080 at 48 FPS (2x enhancement, CRF 18, fast). HD uses an upscaled hosted Wan source rather than native 1080p model generation.

The direct image-to-video path saves the Flux keyframe at 1536x864 instead of unnecessarily enlarging it to 7680x4320 before shrinking it again for the model. Replicate status checks run every 0.5 seconds, and per-stage timings are logged. The Wan fast endpoint accepts only its declared prompt/image/resolution inputs; do not send `num_inference_steps` or `guidance_scale` unless the selected model's API schema supports them. Model cold-start and inference duration are controlled by the hosted provider; this Streamlit app has no public callback endpoint for Replicate webhooks, so a sub-60-second completion cannot be guaranteed by polling changes alone.

Camera motion includes static, dolly/zoom, pan/tilt, 360-degree orbit, crane, subject/forward tracking, handheld, aerial drone, Hitchcock dolly zoom, roll, rack focus, POV, and bullet-time moves. The selected move is validated in the director schema and passed as an explicit motion direction to the hosted video model; local 2D/depth routes approximate supported moves when used.

Lighting includes natural and time-of-day light, window and forest light, studio portrait setups, hard/soft and directional sources, practical lamps, color washes, neon, silhouettes, volumetric shafts, underwater effects, flicker, lasers, and dramatic cinematic looks. All lighting choices share one validated catalog used by the UI and director schema.

Atmosphere options include None, Rain & Storm, Heavy Fog & Mist, Flying Embers & Fire Sparks, Dust Motes & Light Leaks, Blizzard & Snowstorm, Crimson Dust Storm, Thick Smoke & Haze, Ash Fall, Underwater Bubble Flow, Bioluminescent Spores, and Heat Haze Distortion. The selected effect is included in the scene direction used for keyframe and video generation.

Character Action includes camera-motion-only, subtle breathing, cinematic walking, sprinting, turn-and-face, expressive dialogue, facial expression, shouting, sword/martial arts, tactical aiming, strikes, dodging, superhero landing, dramatic gaze, adjusting clothes/armor, and reaching out. Actions are validated and added to both the Flux keyframe direction and hosted motion prompt; legacy action labels remain accepted for existing callers.

Voiceover and ElevenLabs voice/model selection are temporarily hidden in the Ghost Engine Studio UI. The pipeline still supports optional voiceover parameters for future re-enablement.

Set `LAYER6_AMBIENCE_PATH` to a soundscape file to use it as the ambient bed. With no file configured, the master creates a subtle filtered pink-noise ambience. Dialogue receives a light echo, and the mix is limited and loudness normalized. Layer 1 requires `OPENAI_API_KEY`; Layer 2 requires `REPLICATE_API_TOKEN` (or `REPLICATE_API_KEY`); Layer 5 requires a configured TTS provider and Wav2Lip for animated lip sync. `LAYER5_TTS_LANGUAGE` selects the configured TTS language. Layer 5 uses `audio_dialogue`, or the supplied `user_script` as narration when Layer 1 finds no verbatim dialogue.
