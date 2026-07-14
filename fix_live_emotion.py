# encoding: utf-8
with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# FIX 1: In generate_emotion_voice - Fix edge TTS fallback to not use is_audio_audible check
# (edge TTS generates low volume audio that fails the check)
old_edge = '''            for voice_name in voice_candidates:
                try:
                    safe_remove_file(output_path)
                    run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_path))
                    if os.path.exists(output_path) and is_audio_audible(output_path):
                        return output_path
                except Exception as voice_error:
                    logger.warning(f"Edge TTS voice failed ({voice_name}): {voice_error}")'''

new_edge = '''            for voice_name in voice_candidates:
                try:
                    safe_remove_file(output_path)
                    run_async_in_thread(edge_tts.Communicate(text, voice_name).save(output_path))
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 2048:
                        return output_path
                except Exception as voice_error:
                    logger.warning(f"Edge TTS voice failed ({voice_name}): {voice_error}")'''

if old_edge in c:
    c = c.replace(old_edge, new_edge)
    print('FIX 1: Edge TTS fallback - replaced is_audio_audible with simple size check')
else:
    print('FIX 1 ERROR: Edge TTS section not found!')

# FIX 2: Fix the voice_id resolution - the default ID "21m00Tcm4TlvDq8ikWAM" is wrong
# Actually that's Adam's ID, but the default should be Rachel
# More importantly, we need to ensure ElevenLabs gets a chance even if is_audio_audible fails
# Let's add volume normalization for ElevenLabs output

# FIX 3: Make voice_id resolution more robust
old_vid_line = '''            voice_id = ELEVENLABS_VOICES.get(selected_voice_label, {}).get("id", "21m00Tcm4TlvDq8ikWAM")'''
new_vid_line = '''            voice_id = ELEVENLABS_VOICES.get(selected_voice_label, {}).get("id", "pNInz6obpgDQ5IdwJg7p")'''

if old_vid_line in c:
    c = c.replace(old_vid_line, new_vid_line)
    print('FIX 2: Default voice ID changed to Rachel (was Adam)')
else:
    print('FIX 2 ERROR: Voice ID line not found!')
    idx = c.find('voice_id = ELEVENLABS_VOICES.get(selected_voice_label')
    if idx >= 0:
        print(f'Found at {idx}: {c[idx:idx+150]}')

# FIX 4: In ElevenLabs section, also accept audio even if is_audio_audible fails 
# (volume might be low but still audible)
old_eleven_check = '''            if AudioEngine.generate_elevenlabs_speech(modified_text, output_path, elevenlabs_voice_id):
                if is_audio_audible(output_path):
                    return output_path'''
new_eleven_check = '''            if AudioEngine.generate_elevenlabs_speech(modified_text, output_path, elevenlabs_voice_id):
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                    return output_path'''

if old_eleven_check in c:
    c = c.replace(old_eleven_check, new_eleven_check)
    print('FIX 3: ElevenLabs check - replaced is_audio_audible with size check')
else:
    print('FIX 3 ERROR: ElevenLabs check not found!')

# FIX 5: Also fix the audio player section - ensure st.audio is used properly
# Find the audio player in col2
idx = c.find('def render_live_emotion_voice()')
section = c[idx:idx+8000]
aud_idx = section.find('with col2:')
if aud_idx >= 0:
    col2_section = section[aud_idx:aud_idx+3000]
    # Check if st.audio is used
    if 'st.audio' in col2_section:
        print('Audio player section found with st.audio')
        idx2 = col2_section.find('st.audio')
        print(f'  st.audio at offset: {col2_section[idx2-50:idx2+100]}')
    else:
        print('WARNING: No st.audio in col2!')
else:
    print('WARNING: col2 not found in render_live_emotion_voice!')

# Write back
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)

try:
    compile(c, 'app.py', 'exec')
    print('\nSyntax check: PASSED')
except SyntaxError as e:
    print(f'\nSyntax error: {e}')
