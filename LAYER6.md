# Layer 6: neural upscale, spatial audio, master orchestration

Run the complete six-layer pipeline:

```python
from layer6_master_engine import run_zovix_ghost_engine

master_mp4 = run_zovix_ghost_engine(user_script)
```

The orchestrator generates a Flux keyframe, a camera or image-to-video motion clip, and a browser-ready master at `static/outputs/browser_ready_*.mp4`. It logs stage failures and total elapsed time. Intermediate renders are retained for inspection.

Layer 6 uses `realesrgan-ncnn-vulkan` when available (override its executable with `LAYER6_REALESRGAN_BIN`; model with `LAYER6_REALESRGAN_MODEL`). If it is unavailable or fails, FFmpeg uses Lanczos scaling, light denoising for HD, frame-rate conversion, and mild sharpening. The fallback does not synthesize neural texture. Upscaling cannot recover details absent from the source.

The hosted Wan/Replicate endpoint returns an encoded video rather than latent tensors. Ghost Engine requests a five-second clip. Standard uses Wan 480p and HD requests 720p, unless `ZOVIX_GHOST_WAN_RESOLUTION` overrides it. HD sends a larger reference where the inline file limit permits and retains the generated source resolution until mastering. Image-to-video prompts request stable scene geometry while preserving requested motion; model output can still contain visual artifacts. Camera-only clips use a small overscan to prevent reflected borders, so framing is slightly cropped. Clips shorter than requested are rejected instead of padded with a frozen frame. Frame rate is converted without optical-flow interpolation, and hosted inference time depends on provider availability.

Ghost Engine offers two export tiers in both silent and voiceover renders: Standard exports 1280x720 at 30 FPS (CRF 20, ultrafast); HD exports 1920x1080 at 30 FPS (2x enhancement, CRF 18, fast). HD uses an upscaled hosted Wan source rather than native 1080p model generation. Portrait and square output dimensions follow the chosen aspect ratio.

The direct image-to-video path saves the Flux keyframe at 1536x864 instead of unnecessarily enlarging it to 7680x4320 before shrinking it again for the model. Replicate status checks run every 0.5 seconds, and per-stage timings are logged. The Wan fast endpoint accepts only its declared prompt/image/resolution inputs; do not send `num_inference_steps` or `guidance_scale` unless the selected model's API schema supports them. Model cold-start and inference duration are controlled by the hosted provider; this Streamlit app has no public callback endpoint for Replicate webhooks, so a sub-60-second completion cannot be guaranteed by polling changes alone.

The original scene prompt is retained alongside the director's visual direction for both keyframe and motion generation. Explicitly selected camera, lighting, atmosphere, and action controls take precedence when they conflict with the prompt. With Face Lock enabled, the reference is passed to FLUX Kontext Pro; without it, the existing FLUX 1.1 Pro route remains in use. A clear reference showing the character's face and outfit can improve consistency across renders, but neither identity nor every requested detail is guaranteed by the hosted models. Reference-model availability and charges may differ.

Camera motion includes static, dolly/zoom, pan/tilt, 360-degree orbit, crane, subject/forward tracking, handheld, aerial drone, Hitchcock dolly zoom, roll, rack focus, POV, and bullet-time moves. The selected move is validated in the director schema and passed as an explicit motion direction to the hosted video model; local 2D/depth routes approximate supported moves when used.

Lighting includes natural and time-of-day light, window and forest light, studio portrait setups, hard/soft and directional sources, practical lamps, color washes, neon, silhouettes, volumetric shafts, underwater effects, flicker, lasers, and dramatic cinematic looks. All lighting choices share one validated catalog used by the UI and director schema.

Atmosphere options include None, Rain & Storm, Heavy Fog & Mist, Flying Embers & Fire Sparks, Dust Motes & Light Leaks, Blizzard & Snowstorm, Crimson Dust Storm, Thick Smoke & Haze, Ash Fall, Underwater Bubble Flow, Bioluminescent Spores, and Heat Haze Distortion. The selected effect is included in the scene direction used for keyframe and video generation.

Character Action includes camera-motion-only, subtle breathing, cinematic walking, sprinting, turn-and-face, expressive dialogue, facial expression, shouting, sword/martial arts, tactical aiming, strikes, dodging, superhero landing, dramatic gaze, adjusting clothes/armor, and reaching out. Actions are validated and added to both the Flux keyframe direction and hosted motion prompt; legacy action labels remain accepted for existing callers.

Voiceover and ElevenLabs voice/model selection are temporarily hidden in the Ghost Engine Studio UI. The pipeline still supports optional voiceover parameters for future re-enablement.

Set `LAYER6_AMBIENCE_PATH` to a soundscape file to use it as the ambient bed. With no file configured, the master creates a subtle filtered pink-noise ambience. Dialogue receives a light echo, and the mix is limited and loudness normalized. Layer 1 requires `OPENAI_API_KEY`; Layer 2 requires `REPLICATE_API_TOKEN` (or `REPLICATE_API_KEY`); Layer 5 requires a configured TTS provider and Wav2Lip for animated lip sync. `LAYER5_TTS_LANGUAGE` selects the configured TTS language. Layer 5 uses `audio_dialogue`, or the supplied `user_script` as narration when Layer 1 finds no verbatim dialogue.
