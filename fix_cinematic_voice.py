# encoding: utf-8
c = open('engine.py', 'r', encoding='utf-8').read()

old_voice_line = '''            selected_voice_id = "21m00Tcm4TlvDq8ikWAM" if "Drew" in voice_profile else "pNInz6obpgDQ5IdwJg7p"

            if ELEVENLABS_API_KEY:
                voice_built = AudioEngine.generate_elevenlabs_speech(text, audio_segment_path, selected_voice_id)
            if not voice_built:
                AudioEngine.run_fallback_tts(
                    text=text,
                    output_filename=audio_segment_path,
                    language_choice=language_choice,
                    voice_profile=voice_profile,
                )'''

new_voice_line = '''            # Resolve ElevenLabs voice ID from voice_profile name
            selected_voice_id = "pNInz6obpgDQ5IdwJg7p"  # default (Rachel)
            if voice_profile and ELEVENLABS_VOICES:
                voice_meta = ELEVENLABS_VOICES.get(voice_profile)
                if voice_meta and voice_meta.get('voice_id'):
                    selected_voice_id = voice_meta['voice_id']
                else:
                    # Fallback: search by name keywords
                    for vname, vmeta in ELEVENLABS_VOICES.items():
                        if voice_profile.lower() in vname.lower() or vname.lower() in voice_profile.lower():
                            if vmeta.get('voice_id'):
                                selected_voice_id = vmeta['voice_id']
                                break

            if ELEVENLABS_API_KEY:
                voice_built = AudioEngine.generate_elevenlabs_speech(text, audio_segment_path, selected_voice_id)
            if not voice_built:
                AudioEngine.run_fallback_tts(
                    text=text,
                    output_filename=audio_segment_path,
                    language_choice=language_choice,
                    voice_profile=voice_profile,
                )'''

if old_voice_line in c:
    c = c.replace(old_voice_line, new_voice_line)
    print("Voice resolution updated successfully!")
    
    # Write back
    with open('engine.py', 'w', encoding='utf-8') as f:
        f.write(c)
    
    # Verify syntax
    try:
        compile(c, 'engine.py', 'exec')
        print("✅ Syntax check PASSED!")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
else:
    print("ERROR: Could not find old voice line!")
    idx = c.find('selected_voice_id =')
    if idx >= 0:
        print(f'Found at {idx}: {c[idx:idx+200]}')
    else:
        print('selected_voice_id not found at all!')
