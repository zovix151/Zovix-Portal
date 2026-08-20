import re

with open('app.py', encoding='utf-8', errors='replace') as f:
    content = f.read()
    lines = content.splitlines()

patterns = [
    'REPLICATE_API_KEY =',
    'REPLICATE_FACE_MODEL =',
    'REPLICATE_COOLDOWN_FALLBACK_SECONDS',
    'REPLICATE_MAX_THROTTLE_RETRIES',
    'def _get_replicate_api_token',
    'def _run_replicate_face_model',
    'def generate_world_face_video',
    'def generate_face_video',
    'def _extract_video_url_from_replicate_output',
    'def _normalize_api_token',
    'def _set_replicate_last_error',
    'def _is_replicate_throttle_error',
    'def _parse_replicate_retry_seconds',
    'def _set_replicate_cooldown',
    'def _get_replicate_cooldown_remaining',
    'DEEPINFRA',
    'from deepinfra_engine',
    'import deepinfra_engine',
    'def run_unified_face_video_mode',
    'def deepface_scan_face_and_select_voice',
    'def _resolve_face_voice_config',
    'def _synthesize_face_audio_strict',
    'def get_wav2lip_setup_status',
    'def run_wav2lip_cli',
    'ELEVENLABS_VOICES =',
    'HAS_REPLICATE',
    'import replicate',
    'replicate.Client',
    'replicate.run',
    'generate_face_video_real',
]

for i, line in enumerate(lines, 1):
    for p in patterns:
        if p in line:
            print(f"Line {i}: {line.rstrip()[:150]}")
            break

print("\n--- Total lines:", len(lines))