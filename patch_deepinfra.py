"""
================================================================================
ZOVIX — PATCH SCRIPT: Replace Replicate-based generate_face_video() with DeepInfra
================================================================================
This script performs a COMPLETE replacement:

1. Adds DEEPINFRA_API_KEY to the API keys section
2. REMOVES all Replicate-specific code (helpers + generate_world_face_video)
3. COMPLETELY REPLACES generate_face_video() with DeepInfra version:
   - Uses DeepInfraFaceEngine
   - Tries Wav2Lip -> SadTalker -> LivePortrait in sequence
   - Falls back to local Wav2Lip if all DeepInfra models fail
   - Returns video path (local file) or None
4. Keeps ALL other functions unchanged:
   - run_unified_face_video_mode(), ELEVENLABS_VOICES
   - deepface_scan_face_and_select_voice(), _resolve_face_voice_config()
   - _synthesize_face_audio_strict(), get_wav2lip_setup_status(), run_wav2lip_cli()
   - generate_elevenlabs_audio_for_face(), _clamp_face_video_duration()
================================================================================
"""
import sys
import shutil

APP_PATH = 'app.py'
BACKUP_PATH = 'app_backup_before_deepinfra.py'

# ==========================================================================
# READ THE FILE
# ==========================================================================
print(f"Reading {APP_PATH}...")
with open(APP_PATH, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

original_len = len(content)
print(f"File size: {original_len:,} chars")

# Make a backup
shutil.copy(APP_PATH, BACKUP_PATH)
print(f"Backup created: {BACKUP_PATH}")

# ==========================================================================
# STEP 1: Add DEEPINFRA_API_KEY in API keys section
# ==========================================================================
old_repl_key = 'REPLICATE_API_KEY = get_system_secret("REPLICATE_API_KEY")'
new_deep_key = (
    'DEEPINFRA_API_KEY = get_system_secret("DEEPINFRA_API_KEY") or '
    'get_system_secret("DEEPINFRA_API_TOKEN") or os.getenv("DEEPINFRA_API_KEY", "")\n'
    'DEEPINFRA_FACE_MODEL = get_system_secret("DEEPINFRA_FACE_MODEL", "") or os.getenv("DEEPINFRA_FACE_MODEL", "")'
)

if old_repl_key in content:
    if 'DEEPINFRA_API_KEY =' not in content:
        content = content.replace(old_repl_key, old_repl_key + '\n' + new_deep_key, 1)
        print("[STEP 1] DEEPINFRA_API_KEY added")
    else:
        print("[STEP 1] SKIP: DEEPINFRA_API_KEY already present")
else:
    print("[STEP 1] WARN: Could not find REPLICATE_API_KEY line")

# ==========================================================================
# STEP 2: REMOVE Replicate-specific helper functions
# (from _extract_video_url_from_replicate_output through generate_world_face_video)
# but KEEP _clamp_face_video_duration
# ==========================================================================

# Find the start of Replicate helpers (before the clamp function)
repl_start_marker = 'def _extract_video_url_from_replicate_output(output_obj):'
repl_start = content.find(repl_start_marker)

# Find _clamp_face_video_duration - we need to keep this but remove the functions before it
clamp_marker = 'def _clamp_face_video_duration(duration):'
clamp_pos = content.find(clamp_marker)

# Find _is_replicate_throttle_error - these come after clamp and need removal
throttle_marker = 'def _is_replicate_throttle_error(err_text):'
throttle_pos = content.find(throttle_marker)

# Find generate_face_video - the Replicate helpers end right before this
gv_marker = 'def generate_face_video(prompt'
gv_pos = content.find(gv_marker)

print(f"  _extract_video_url_from_replicate_output at: {repl_start}")
print(f"  _clamp_face_video_duration at: {clamp_pos}")
print(f"  _is_replicate_throttle_error at: {throttle_pos}")
print(f"  generate_face_video at: {gv_pos}")

if repl_start >= 0 and gv_pos > repl_start:
    # Remove everything from the start of replicate helpers to just before generate_face_video
    # But KEEP _clamp_face_video_duration
    # The structure is:
    #   _extract_video_url_from_replicate_output  <- REMOVE
    #   _normalize_api_token                       <- REMOVE  
    #   _set_replicate_last_error                  <- REMOVE
    #   _clamp_face_video_duration                 <- KEEP
    #   _is_replicate_throttle_error               <- REMOVE
    #   _parse_replicate_retry_seconds             <- REMOVE
    #   _set_replicate_cooldown                    <- REMOVE
    #   _get_replicate_cooldown_remaining          <- REMOVE
    #   _get_replicate_api_token                   <- REMOVE
    #   _run_replicate_face_model                  <- REMOVE
    #   generate_world_face_video                  <- REMOVE
    
    # Find the end of _set_replicate_last_error (right before _clamp_face_video_duration)
    # Find what comes immediately BEFORE _set_replicate_last_error
    # We need to find where the section of removable code starts
    # First, check for _set_replicate_last_error
    sle_marker = 'def _set_replicate_last_error(message):'
    sle_pos = content.find(sle_marker)
    if sle_pos >= 0:
        # Remove from the start of the section before _extract up to where _clamp starts
        # But we need to preserve the section before _extract
        # Find the line start of _extract section (including any preceding blank lines/comments)
        
        # Remove: from start of _extract to just before _clamp
        # Then remove: from just after _clamp's end to just before generate_face_video
        
        # Find the beginning of the section before _extract (previous newlines)
        # Look for the comment block or previous assignment
        # Find the last newline before repl_start that follows blank lines
        pre_repl = content.rfind('\n\n', 0, repl_start)
        if pre_repl >= 0:
            section_start = pre_repl + 2  # Skip the double newline
        else:
            section_start = repl_start
        
        # The removable sections are:
        # 1. From section_start to clamp_pos (includes _extract, _normalize, _set_last_error)
        # 2. From after clamp function ends to gv_pos (includes throttle through world_video)
        # But we need to find where clamp ends
        # Find the next function def after clamp
        next_after_clamp = content.find('def ', clamp_pos + len(clamp_marker))
        # The clamp function body ends right before the next def
        # But we should search for the actual next def carefully
        all_defs = []
        idx = 0
        while True:
            idx = content.find('\ndef ', idx)
            if idx < 0:
                break
            all_defs.append(idx + 1)
            idx += 1
        
        # Find clamp position in all_defs
        clamp_def_idx = None
        for i, d in enumerate(all_defs):
            if d <= clamp_pos and (i + 1 >= len(all_defs) or all_defs[i + 1] > clamp_pos):
                clamp_def_idx = i
                break
        
        if clamp_def_idx is not None and clamp_def_idx + 1 < len(all_defs):
            clamp_end = all_defs[clamp_def_idx + 1]
            
            # Also find where _set_replicate_last_error section starts
            # It starts right before _clamp
            # Remove section 1: from section_start to clamp_pos
            new_content = content[:section_start] + content[clamp_pos:]
            
            # Now remove section 2: from clamp_end to gv_pos
            # Find the new clamp_pos in new_content (it's at index section_start)
            new_clamp_pos = section_start
            # Find where clamp function ends in new_content
            new_clamp_end = new_clamp_pos + (clamp_end - clamp_pos)
            # Find gv_pos in new_content
            new_gv_pos = new_clamp_end + (gv_pos - clamp_end)
            
            new_content = new_content[:new_clamp_end] + new_content[new_gv_pos:]
            
            content = new_content
            print("[STEP 2] REMOVED Replicate helper functions + generate_world_face_video")
            print(f"         Kept _clamp_face_video_duration")
            print(f"  New file size: {len(content):,} chars")
        else:
            print("[STEP 2] ERROR: Could not determine clamp function boundaries")
            sys.exit(1)
    else:
        print("[STEP 2] ERROR: Could not find _set_replicate_last_error")
        sys.exit(1)
else:
    print("[STEP 2] ERROR: Could not find Replicate helper section")
    sys.exit(1)

# ==========================================================================
# STEP 3: REPLACE generate_face_video() with DeepInfra version
# ==========================================================================
new_face_video_fn = '''def generate_face_video(prompt, face_image_path, duration=30, emotion="neutral", camera_angle="front", quality="Standard", voice_language=None, voice_label=None):
    """Face Video Generation via DeepInfra (Wav2Lip -> SadTalker -> LivePortrait -> Local Fallback).

    Tries DeepInfra cloud models in sequence, then falls back to local Wav2Lip
    if all cloud models fail. Returns path to generated video or None.
    """
    if not face_image_path or not os.path.exists(face_image_path):
        logger.error(f"[DeepInfra] Face image not found: {face_image_path}")
        return None

    try:
        os.makedirs("face_videos", exist_ok=True)
        engine = DeepInfraFaceEngine()

        if not engine.is_available():
            logger.warning("[DeepInfra] Engine/API key not available - falling back to local Wav2Lip")
            return _run_local_wav2lip_fallback(prompt, face_image_path, duration, quality)

        # ---- Resolve voice config ----
        voice_cfg = _resolve_face_voice_config(
            voice_language=voice_language,
            voice_label=voice_label,
            preferred_gender=st.session_state.get('fv_detected_gender') if st.session_state.get('fv_gender_auto', False) else None
        )

        # ---- Synthesize audio ----
        audio_path = None
        try:
            audio_path = f"face_videos/_face_audio_{uuid.uuid4().hex[:8]}.mp3"
            audio_ok = _synthesize_face_audio_strict(
                prompt or "Hello, this is my AI video.",
                audio_path,
                voice_cfg,
                duration_hint=_clamp_face_video_duration(duration)
            )
            if not audio_ok or not os.path.exists(audio_path):
                audio_path = None
        except Exception as e:
            logger.warning(f"[DeepInfra] Audio synthesis failed: {e}")
            audio_path = None

        if not audio_path or not os.path.exists(audio_path):
            logger.warning("[DeepInfra] No valid audio - using tone fallback")
            audio_path = _create_tone_audio(_clamp_face_video_duration(duration))

        if not audio_path or not os.path.exists(audio_path):
            logger.error("[DeepInfra] No audio available for generation")
            return None

        # ---- Try DeepInfra models in sequence: Wav2Lip -> SadTalker -> LivePortrait ----
        last_error = None
        for model_name in ["wav2lip", "sadtalker", "liveportrait"]:
            try:
                logger.info(f"[DeepInfra] Trying {model_name} via DeepInfra...")
                if model_name == "wav2lip":
                    out = engine.generate_wav2lip(
                        face_image_path,
                        audio_path,
                        quality=quality,
                        progress_callback=lambda msg, pct: None
                    )
                elif model_name == "sadtalker":
                    out = engine.generate_sadtalker(
                        face_image_path,
                        audio_path,
                        quality=quality,
                        pose_style="frontal",
                        expression_scale=1.2,
                        progress_callback=lambda msg, pct: None
                    )
                else:
                    out = engine.generate_liveportrait(
                        face_image_path,
                        audio_path,
                        quality=quality,
                        motion_level="high",
                        progress_callback=lambda msg, pct: None
                    )

                if out and os.path.exists(out):
                    logger.info(f"[DeepInfra] {model_name} succeeded: {out}")
                    st.session_state["face_video_engine_used"] = f"DeepInfra ({model_name})"
                    st.session_state["face_video_runtime_mode"] = "Cloud"
                    safe_remove_file(audio_path) if audio_path else None
                    return out
                else:
                    last_error = f"{model_name} returned None"
                    logger.warning(f"[DeepInfra] {model_name} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[DeepInfra] {model_name} raised: {last_error}")

        # ---- Fallback: Local Wav2Lip ----
        logger.warning(f"[DeepInfra] All DeepInfra models failed ({last_error}) - falling back to local Wav2Lip")
        return _run_local_wav2lip_fallback(prompt, face_image_path, duration, quality)

    except Exception as e:
        logger.error(f"[DeepInfra] generate_face_video error: {e}")
        try:
            return _run_local_wav2lip_fallback(prompt, face_image_path, duration, quality)
        except Exception as e2:
            logger.error(f"[DeepInfra] Local fallback also failed: {e2}")
            return None


def _detect_face_gender(face_image_path):
    """Quick gender detector using deepface if available, else returns None."""
    try:
        from deepface import DeepFace
        result = DeepFace.analyze(img_path=face_image_path, actions=('age', 'gender'), enforce_detection=False)
        if isinstance(result, list) and result:
            return result[0].get("dominant_gender", "").lower()
        elif isinstance(result, dict):
            return result.get("dominant_gender", "").lower()
    except Exception:
        pass
    return None


def _create_tone_audio(duration_seconds=5.0):
    """Create a simple tone WAV file if no real audio is available."""
    import wave
    import struct
    import math

    os.makedirs("face_videos", exist_ok=True)
    path = f"face_videos/_tone_{uuid.uuid4().hex[:8]}.wav"
    freq = 440.0
    sample_rate = 44100
    n_frames = int(sample_rate * max(0.5, min(duration_seconds, 20)))

    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_frames):
            val = int(32767 * 0.15 * math.sin(2 * math.pi * freq * i / sample_rate))
            wf.writeframes(struct.pack('<h', val))
    return path


def _run_local_wav2lip_fallback(prompt, face_image_path, duration, quality):
    """Run local Wav2Lip CLI as a final fallback."""
    logger.info("[DeepInfra] Attempting local Wav2Lip fallback...")
    try:
        status = get_wav2lip_setup_status()
        if not status or not status.get("ready", False):
            logger.error("[DeepInfra] Local Wav2Lip not ready")
            return None

        audio_path = f"face_videos/_fallback_audio_{uuid.uuid4().hex[:8]}.mp3"
        try:
            voice_cfg = _resolve_face_voice_config(voice_language=None, voice_label=None)
            _synthesize_face_audio_strict(prompt or "Hello! This is a Zovix AI generated video.", audio_path, voice_cfg, duration_hint=duration)
        except Exception:
            audio_path = _create_tone_audio(duration)

        out_path = f"face_videos/wav2lip_local_{uuid.uuid4().hex[:8]}.mp4"
        os.makedirs("face_videos", exist_ok=True)
        result = run_wav2lip_cli(
            face_image_path=face_image_path,
            audio_path=audio_path,
            output_video_path=out_path,
            width=512,
            height=512,
            fps=24
        )
        if result and os.path.exists(out_path):
            st.session_state["face_video_engine_used"] = "Wav2Lip (Local Fallback)"
            st.session_state["face_video_runtime_mode"] = "Local"
            safe_remove_file(audio_path) if audio_path else None
            return out_path
    except Exception as e:
        logger.error(f"[DeepInfra] Local Wav2Lip fallback error: {e}")
    return None
'''

# Find generate_face_video in the modified content and replace it
gv_marker_new = 'def generate_face_video(prompt'
gv_pos_new = content.find(gv_marker_new)

if gv_pos_new >= 0:
    # Find the next function after generate_face_video
    remaining = content[gv_pos_new + len(gv_marker_new):]
    next_func_pos = remaining.find('\ndef ')
    if next_func_pos >= 0:
        end_of_fn = gv_pos_new + len(gv_marker_new) + next_func_pos
        content = content[:gv_pos_new] + new_face_video_fn + content[end_of_fn:]
        print("[STEP 3] generate_face_video() REPLACED with DeepInfra version")
    else:
        print("[STEP 3] ERROR: Could not find next function after generate_face_video")
        sys.exit(1)
else:
    print("[STEP 3] ERROR: Could not find generate_face_video in modified content")
    sys.exit(1)

# ==========================================================================
# WRITE THE FILE
# ==========================================================================
with open(APP_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

new_len = len(content)
print(f"\n=== COMPLETE ===")
print(f"Original size: {original_len:,} chars")
print(f"New size:      {new_len:,} chars")
print(f"Removed:       {original_len - new_len:,} chars")
print(f"Backup:        {BACKUP_PATH}")