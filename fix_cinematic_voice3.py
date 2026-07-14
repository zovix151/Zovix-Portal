c = open('engine.py', 'r', encoding='utf-8').read()

# Replace the ELEVENLABS_VOICES lookup with our new function lookup
old_lookup = '''            # Resolve ElevenLabs voice ID from voice_profile name
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
                                break'''

new_lookup = '''            # Resolve ElevenLabs voice ID from voice_profile name
            selected_voice_id = _resolve_cinematic_voice_id(voice_profile)'''

if old_lookup in c:
    c = c.replace(old_lookup, new_lookup)
    print('Replaced ELEVENLABS_VOICES lookup with _resolve_cinematic_voice_id')
    
    with open('engine.py', 'w', encoding='utf-8') as f:
        f.write(c)
    
    try:
        compile(c, 'engine.py', 'exec')
        print('✅ Syntax check PASSED!')
    except SyntaxError as e:
        print(f'❌ Syntax error: {e}')
else:
    print('ERROR: Could not find old lookup block!')
    idx = c.find('_resolve_cinematic_voice_id')
    if idx >= 0:
        print(f'Found _resolve_cinematic_voice_id at {idx}')
        print(c[idx:idx+300])
    idx2 = c.find('ELEVENLABS_VOICES')
    if idx2 >= 0:
        print(f'Found ELEVENLABS_VOICES at {idx2}')
        print(c[idx2:idx2+200])
