c = open('engine.py', 'r', encoding='utf-8').read()

# Find the mix_cmd section in build_scene_stitched_video_isolated
old_mix = """            if bgm_path and os.path.exists(bgm_path):
                mix_cmd = [
                    'ffmpeg', *get_hwaccel_args(), '-y', '-i', temp_stitched_output, '-stream_loop', '-1', '-i', bgm_path,
                    '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first[aout]',
                    '-map', '0:v:0', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', video_output
                ]"""

new_mix = """            if bgm_path and os.path.exists(bgm_path):
                # Get voice (stitched) audio duration to properly trim BGM
                _dur_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', temp_stitched_output]
                _dur_result = subprocess.run(_dur_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    _voice_dur = float(_dur_result.stdout.strip())
                except:
                    _voice_dur = 30.0
                mix_cmd = [
                    'ffmpeg', *get_hwaccel_args(), '-y', '-i', temp_stitched_output, '-i', bgm_path,
                    '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f},atrim=0:{_voice_dur:.2f}[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]',
                    '-map', '0:v:0', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', video_output
                ]"""

if old_mix in c:
    c = c.replace(old_mix, new_mix)
    print('FIX: Replaced BGM mixing command - removed -stream_loop -1, added atrim + dropout_transition')
else:
    print('ERROR: Original mix_cmd not found!')
    # Find it
    idx = c.find('bgm_path and os.path.exists(bgm_path)')
    if idx >= 0:
        print(f'Found at {idx}:')
        print(c[idx:idx+600])
    else:
        print('No BGM mixing section found in engine.py!')

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(c)

try:
    compile(c, 'engine.py', 'exec')
    print('\nSyntax check: PASSED')
except SyntaxError as e:
    print(f'Syntax error: {e}')
