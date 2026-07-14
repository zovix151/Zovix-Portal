c = open('engine.py', 'r', encoding='utf-8').read()
idx = c.find('bgm_path and os.path.exists(bgm_path)')
print('=== NEW BGM MIXING CODE ===')
print(c[idx:idx+800])
print()

# Verify app.py
c2 = open('app.py', 'r', encoding='utf-8').read()

# Check using .find() instead of string literal
if c2.find('st.session_state.get("studio_audio_bgm_volume_slider", 0.3)') >= 0:
    print('app.py: session_state BGM volume reference OK')
else:
    print('app.py: session_state BGM volume reference MISSING')

if c2.find('st.slider("BGM Audio Level Mixer"') >= 0:
    print('app.py: BGM volume slider preserved')
else:
    print('app.py: BGM volume slider MISSING')

try:
    compile(c, 'engine.py', 'exec')
    compile(c2, 'app.py', 'exec')
    print('Both files syntax OK')
except SyntaxError as e:
    print(f'Syntax error: {e}')
