"""
EMOTION VOICE FIX - Apply 3 fixes to app.py:
1. Detailed st.error() with exact exception message
2. Devanagari script auto-detection for Hindi
3. API key pre-check before TTS tiers

This script handles BOTH cases:
- If generate_emotion_voice() exists in app.py, it replaces it
- If it doesn't exist, it inserts before render_live_emotion_voice()
"""

import re
import sys

print("Reading app.py...")
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if generate_emotion_voice exists
func_idx = content.find('def generate_emotion_voice(')
func_exists = func_idx >= 0
print(f"generate_emotion_voice exists in app.py: {func_exists}")

# ============================================================
# NEW FUNCTION WITH ALL 3 FIXES
# ============================================================
new_function = '''def generate_emotion_voice(text, emotion="neutral", voice_type="male", output_path=None, elevenlabs_voice_id=None):
    """Generate emotion-infused voice with 5-tier cascade TTS.
    
    FIXED 2026-08-09:
    - st.error() shows exact exception message, not just "Voice generation failed"
    - Auto-detect Devanagari (Hindi) script via regex, force Hindi voice model
    - Check all TTS API keys first, warn user if none are configured
    """
    if not output_path:
        output_path = f"emotion_voice_outputs/emotion_{uuid.uuid4().hex[:8]}.mp3"
    os.makedirs("emotion_voice_outputs", exist_ok=True)
    safe_remove_file(output_path)

    # --- Helper: log + show exact error in Streamlit (FIX 1) ---
    def _fail(msg: str):
        logger.error(msg)
        st.error(f"Voice generation failed: {msg}")

    # ================================================================
    # FIX 2: DEVANAGARI SCRIPT DETECTION
    # If text contains Hindi/Devanagari Unicode chars, force Hindi voice
    # ================================================================
    has_devanagari = bool(re.search(r'[\\u0900-\\u097F]', text)) if text else False
    user_language = st.session_state.get("emotion_voice_language", "English")
    use_hindi_voice = (
        has_devanagari or 
        "Hindi" in user_language or 
        "Hinglish" in user_language
    )
    if has_devanagari:
        logger.info("Devanagari script detected - auto-enabling Hindi voice model")

    # ================================================================
    # FIX 3: API KEY COLLECTION & PRE-CHECK
    # ================================================================
    available_tiers = []

    eleven_key = os.getenv("ELEVENLABS_API_KEY") or get_system_secret("ELEVENLABS_API_KEY")
    if eleven_key:
        available_tiers.append("ElevenLabs")

    azure_key = os.getenv("AZURE_SPEECH_KEY") or get_system_secret("AZURE_SPEECH_KEY")
    azure_region = os.getenv("AZURE_SPEECH_REGION") or get_system_secret("AZURE_SPEECH_REGION", "eastus")
    if azure_key and azure_region:
        available_tiers.append("Azure")

    google_key = os.getenv("GOOGLE_TTS_API_KEY") or get_system_secret("GOOGLE_TTS_API_KEY")
    if not google_key:
        google_key = os.getenv("GEMINI_API_KEY") or get_system_secret("GEMINI_API_KEY")
    if google_key:
        available_tiers.append("Google")

    if edge_tts is not None:
        available_tiers.append("Edge-TTS")
    available_tiers.append("GenerativeFallback")

    logger.info(f"TTS tiers available: {available_tiers}")
    if len(available_tiers) <= 1:  # Only fallback (no real TTS keys)
        st.warning("No TTS API keys configured (ElevenLabs/Azure/Google). Using built-in tone generator only. Set ELEVENLABS_API_KEY, AZURE_SPEECH_KEY, or GEMINI_API_KEY for real voice synthesis.")

    # ================================================================
    # TIER 1: ELEVENLABS (BEST QUALITY)
    # ================================================================
    if eleven_key and elevenlabs_voice_id:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": eleven_key,
            }
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 2000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 2000:
                    logger.info(f"ElevenLabs OK: {text[:40]}... [emotion={emotion}]")
                    return output_path
            elif resp.status_code == 401:
                _fail(f"ElevenLabs: Invalid API key (HTTP 401)")
            elif resp.status_code == 429:
                _fail("ElevenLabs: Quota exceeded (HTTP 429). Check your usage limits.")
            else:
                logger.warning(f"ElevenLabs HTTP {resp.status_code}: {resp.text[:200]}")
        except requests.exceptions.Timeout:
            _fail("ElevenLabs: Request timed out (30s)")
        except requests.exceptions.ConnectionError as e:
            _fail(f"ElevenLabs: Connection error - {e}")
        except Exception as e:
            _fail(f"ElevenLabs: {str(e)}")

    # ================================================================
    # TIER 2: AZURE TTS
    # ================================================================
    if azure_key and azure_region:
        try:
            voice_name = ("hi-IN-MadhurNeural" if voice_type == "male" else "hi-IN-SwaraNeural") if use_hindi_voice else ("en-US-GuyNeural" if voice_type == "male" else "en-US-JennyNeural")

            url = f"https://{azure_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            headers = {
                "Ocp-Apim-Subscription-Key": azure_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
            }

            if use_hindi_voice:
                ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="hi-IN"><voice name="{voice_name}"><prosody rate="0%" pitch="0%">{text}</prosody></voice></speak>'
            else:
                ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name="{voice_name}"><mstts:express-as style="cheerful"><prosody rate="0%" pitch="0%">{text}</prosody></mstts:express-as></voice></speak>'

            resp = requests.post(url, headers=headers, data=ssml, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                if os.path.exists(output_path) and is_audio_audible(output_path):
                    logger.info(f"Azure OK: {text[:40]}... [voice={voice_name}]")
                    return output_path
            elif resp.status_code == 401:
                _fail(f"Azure: Invalid subscription key (HTTP 401)")
            elif resp.status_code == 429:
                _fail("Azure: Quota exceeded (HTTP 429). Check your Azure portal.")
            else:
                logger.warning(f"Azure HTTP {resp.status_code}: {resp.text[:200]}")
        except requests.exceptions.Timeout:
            _fail("Azure TTS: Request timed out (30s)")
        except requests.exceptions.ConnectionError as e:
            _fail(f"Azure TTS: Connection error - {e}")
        except Exception as e:
            _fail(f"Azure TTS: {str(e)}")

    # ================================================================
    # TIER 3: GOOGLE CLOUD TTS
    # ================================================================
    if google_key:
        try:
            import base64 as _b64
            ssml_gender = "MALE" if voice_type == "male" else "FEMALE"
            lang_code = "hi-IN" if use_hindi_voice else "en-US"

            payload = {
                "input": {"text": text},
                "voice": {"languageCode": lang_code, "ssmlGender": ssml_gender},
                "audioConfig": {"audioEncoding": "MP3"},
            }
            resp = requests.post(
                f"https://texttospeech.googleapis.com/v1/text:synthesize?key={google_key}",
                json=payload, timeout=30,
            )
            if resp.status_code == 200:
                audio_content = resp.json().get("audioContent")
                if audio_content:
                    with open(output_path, "wb") as f:
                        f.write(_b64.b64decode(audio_content))
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 2000:
                        logger.info(f"Google OK: {text[:40]}...")
                        return output_path
            elif resp.status_code == 403:
                _fail(f"Google TTS: API key forbidden (HTTP 403). Check key restrictions.")
            elif resp.status_code == 429:
                _fail("Google TTS: Quota exceeded (HTTP 429).")
            else:
                logger.warning(f"Google TTS HTTP {resp.status_code}: {resp.text[:200]}")
        except requests.exceptions.Timeout:
            _fail("Google TTS: Request timed out (30s)")
        except requests.exceptions.ConnectionError as e:
            _fail(f"Google TTS: Connection error - {e}")
        except Exception as e:
            _fail(f"Google TTS: {str(e)}")

    # ================================================================
    # TIER 4: EDGE TTS (FREE, RELIABLE)
    # ================================================================
    try:
        if edge_tts is not None:
            if use_hindi_voice:
                voice_candidates = [
                    "hi-IN-MadhurNeural" if voice_type == "male" else "hi-IN-SwaraNeural",
                    "en-IN-PrabhatNeural" if voice_type == "male" else "en-IN-NeerjaNeural",
                    "en-US-GuyNeural" if voice_type == "male" else "en-US-AriaNeural",
                ]
            else:
                voice_candidates = [
                    "en-US-GuyNeural" if voice_type == "male" else "en-US-AriaNeural",
                    "en-GB-RyanNeural" if voice_type == "male" else "en-GB-SoniaNeural",
                    "en-IN-PrabhatNeural" if voice_type == "male" else "en-IN-NeerjaNeural",
                ]

            for voice_name in voice_candidates:
                try:
                    safe_remove_file(output_path)
                    run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_path))
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 2048:
                        logger.info(f"Edge-TTS OK: {text[:40]}... [voice={voice_name}]")
                        return output_path
                except Exception as voice_error:
                    logger.warning(f"Edge-TTS voice '{voice_name}' failed: {voice_error}")
                    continue
        else:
            logger.warning("edge_tts module not available")
    except Exception as e:
        _fail(f"Edge-TTS: {str(e)}")

    # ================================================================
    # TIER 5: GENERATIVE FALLBACK (ALWAYS WORKS)
    # ================================================================
    try:
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            logger.info(f"Fallback: tone generator for {text[:30]}...")
            import struct
            import math

            sample_rate = 22050
            duration = max(2.0, len(text) * 0.08)
            num_samples = int(sample_rate * duration)

            freq_map = {"neutral": 220, "happy": 440, "sad": 180, "angry": 330, "excited": 550, "serious": 150, "mysterious": 100}
            amp_map = {"neutral": 0.3, "happy": 0.4, "sad": 0.2, "angry": 0.5, "excited": 0.5, "serious": 0.25, "mysterious": 0.15}
            freq = freq_map.get(emotion, 220)
            amplitude = amp_map.get(emotion, 0.3)

            samples = []
            for i in range(num_samples):
                t = i / sample_rate
                vibrato = math.sin(2 * math.pi * 5 * t) * 0.1 if emotion in ("happy", "excited", "sad") else 0
                value = amplitude * math.sin(2 * math.pi * freq * t + vibrato * 2 * math.pi)
                value += 0.3 * amplitude * math.sin(2 * math.pi * freq * 2 * t)
                value += 0.1 * amplitude * math.sin(2 * math.pi * freq * 3 * t)
                value = max(-1.0, min(1.0, value))
                samples.append(struct.pack("h", int(value * 32767)))

            import wave
            with wave.open(output_path, "w") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b"".join(samples))

            mp3_path = output_path.replace(".mp3", "_temp.mp3")
            cmd = ["ffmpeg", "-y", "-i", output_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
                    safe_remove_file(output_path)
                    shutil.move(mp3_path, output_path)
            except Exception:
                safe_remove_file(mp3_path)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"Fallback OK: {text[:30]}... [emotion={emotion}]")
                return output_path

    except Exception as e:
        _fail(f"Tone generator fallback also failed: {str(e)}")

    # All tiers exhausted
    safe_remove_file(output_path)
    _fail("All TTS providers failed. Check API keys, quotas, and network connectivity.")
    return None
'''


if func_exists:
    # REPLACE existing function
    rest = content[func_idx:]
    next_markers = list(re.finditer(r'(?<=\n)(?:def |class |# ===)', rest))
    if next_markers:
        func_end = func_idx + next_markers[0].start()
        new_content = content[:func_idx] + new_function + content[func_end:]
        action = "REPLACED"
    else:
        print("ERROR: Could not find end of function")
        sys.exit(1)
else:
    # INSERT before render_live_emotion_voice
    render_idx = content.find('def render_live_emotion_voice()')
    if render_idx < 0:
        print("ERROR: render_live_emotion_voice not found in app.py!")
        sys.exit(1)
    new_content = content[:render_idx] + '\n\n' + new_function + '\n\n' + content[render_idx:]
    action = "INSERTED"

print(f"Writing updated app.py ({action} generate_emotion_voice)...")
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

# Verify syntax
try:
    compile(new_content, 'app.py', 'exec')
    print(f"SUCCESS: app.py compiles OK! Function {action}.")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    print(f"  Context: {e.text}")
    sys.exit(1)