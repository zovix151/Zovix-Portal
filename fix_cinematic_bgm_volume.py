c = open('app.py','r',encoding='utf-8').read()
idx = c.find('def run_cinematic_engine()')
section = c[idx:idx+36000]

# Find: compilation_thread = threading.Thread(target=internal_thread_worker, args=(data_snapshot, scenes, "final_shorts.mp4", effective_bgm_path, bgm_volume, render_status_dict), daemon=True)
# The bgm_volume there references a local variable that doesn't exist in this scope!
# Fix: Use st.session_state["studio_audio_bgm_volume_slider"] instead

old = 'compilation_thread = threading.Thread(target=internal_thread_worker, args=(data_snapshot, scenes, "final_shorts.mp4", effective_bgm_path, bgm_volume, render_status_dict), daemon=True)'
new = 'compilation_thread = threading.Thread(target=internal_thread_worker, args=(data_snapshot, scenes, "final_shorts.mp4", effective_bgm_path, st.session_state.get("studio_audio_bgm_volume_slider", 0.3), render_status_dict), daemon=True)'

if old in c:
    c = c.replace(old, new)
    print('FIX 1: compilation_thread bgm_volume replaced with session_state value')
else:
    print('FIX 1 ERROR: compilation_thread line not found!')
    idx2 = c.find('compilation_thread = threading.Thread')
    if idx2 >= 0:
        print(f'Found at {idx2}: {c[idx2:idx2+250]}')

# Also fix the internal_thread_worker definition to use session_state if bgm_volume is 0
# Actually the worker gets bgm_volume as param, which is now correct from session_state
# But let me also check if there's bgm_volume slider variable shadowing issue

# Check if bgm_volume is used before slider definition in render flow
# The issue is that bgm_volume = st.slider happens in the parameters_col, not in the render block
# Let me also check the 'deepseek_final_render_btn' path
idx3 = c.find('deepseek_final_render_btn')
if idx3 >= 0:
    print(f'\nFound deepseek_final_render_btn at {idx3}')
    # Check if bgm_volume is passed there too
    print(c[idx3:idx3+1000])
    
    old2 = 'compilation_thread = threading.Thread(target=internal_thread_worker, args=(data_snapshot, scenes, "final_shorts.mp4", effective_bgm_path, bgm_volume, render_status_dict), daemon=True)'
    # Find the second instance
    idx4 = c.find(old2, idx3)
    if idx4 >= 0:
        print(f'\nSecond compilation_thread at {idx4}')
        c = c[:idx4] + 'compilation_thread = threading.Thread(target=internal_thread_worker, args=(data_snapshot, scenes, "final_shorts.mp4", effective_bgm_path, st.session_state.get("studio_audio_bgm_volume_slider", 0.3), render_status_dict), daemon=True)' + c[idx4+len(old2):]
        print('FIX 2: Second compilation_thread also fixed')
    else:
        print('No second compilation_thread instance')
else:
    print('No deepseek_final_render_btn section found')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)

try:
    compile(c, 'app.py', 'exec')
    print('\nSyntax check: PASSED')
except SyntaxError as e:
    print(f'Syntax error: {e}')
