import subprocess, os

print("Creating test audio files...")

# Create a 3-second voice track (440 Hz sine tone, mp3)
cmd_voice = [
    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
    '-c:a', 'libmp3lame', '-b:a', '128k', 'test_voice.mp3'
]
r = subprocess.run(cmd_voice, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(f"Voice file: {os.path.getsize('test_voice.mp3') if os.path.exists('test_voice.mp3') else 'FAIL'} bytes")

# Create a 10-second BGM track (220 Hz sine tone)
cmd_bgm = [
    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=220:duration=10',
    '-c:a', 'libmp3lame', '-b:a', '128k', 'test_bgm.mp3'
]
r = subprocess.run(cmd_bgm, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(f"BGM file: {os.path.getsize('test_bgm.mp3') if os.path.exists('test_bgm.mp3') else 'FAIL'} bytes")

# TEST: Current approach as in engine.py (stream_loop -1, amix)
print("\n=== TEST: Current approach from engine.py ===")
bgm_volume = 0.3
cmd_mix = [
    'ffmpeg', '-y',
    '-i', 'test_voice.mp3',
    '-stream_loop', '-1', '-i', 'test_bgm.mp3',
    '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first[aout]',
    '-map', '[aout]', '-c:a', 'libmp3lame', '-b:a', '192k', 'test_mix.mp3'
]
result = subprocess.run(cmd_mix, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(f"Result: {'SUCCESS' if result.returncode == 0 else 'FAILED'}")
if result.returncode != 0:
    print(f"Error: {result.stderr[-500:]}")
else:
    sz = os.path.getsize('test_mix.mp3')
    print(f"Output file size: {sz} bytes")
    if sz > 0:
        # Check duration
        cmd_dur = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', 'test_mix.mp3']
        dur = subprocess.run(cmd_dur, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Duration: {dur.stdout.strip()}s")
        
        # Volume detect
        cmd_vol = ['ffmpeg', '-hide_banner', '-i', 'test_mix.mp3', '-af', 'volumedetect', '-f', 'null', 'NUL']
        vol = subprocess.run(cmd_vol, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Extract max_volume
        for line in (vol.stderr or '').split('\n'):
            if 'max_volume' in line or 'mean_volume' in line:
                print(f"  {line.strip()}")

# Now test: What if we change order? voice first, BGM second
print("\n=== TEST 2: Voice first input, BGM second (current) ===")
cmd_mix2 = [
    'ffmpeg', '-y',
    '-i', 'test_voice.mp3',
    '-stream_loop', '-1', '-i', 'test_bgm.mp3',
    '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]',
    '-map', '[aout]', '-c:a', 'libmp3lame', '-b:a', '192k', 'test_mix2.mp3'
]
result2 = subprocess.run(cmd_mix2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if result2.returncode == 0:
    sz2 = os.path.getsize('test_mix2.mp3')
    print(f"Output: {sz2} bytes")
    if sz2 > 0:
        cmd_vol2 = ['ffmpeg', '-hide_banner', '-i', 'test_mix2.mp3', '-af', 'volumedetect', '-f', 'null', 'NUL']
        vol2 = subprocess.run(cmd_vol2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in (vol2.stderr or '').split('\n'):
            if 'max_volume' in line or 'mean_volume' in line:
                print(f"  {line.strip()}")
else:
    print(f"Failed: {result2.stderr[-300:]}")

# TEST 3: Different volume levels to verify control
print("\n=== TEST 3: BGM volume = 0.05 (very quiet) ===")
cmd_mix3 = [
    'ffmpeg', '-y',
    '-i', 'test_voice.mp3',
    '-stream_loop', '-1', '-i', 'test_bgm.mp3',
    '-filter_complex', '[0:a]volume=1.0[a0];[1:a]volume=0.05[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]',
    '-map', '[aout]', '-c:a', 'libmp3lame', '-b:a', '192k', 'test_mix3.mp3'
]
result3 = subprocess.run(cmd_mix3, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if result3.returncode == 0:
    sz3 = os.path.getsize('test_mix3.mp3')
    print(f"Output: {sz3} bytes")
    if sz3 > 0:
        cmd_vol3 = ['ffmpeg', '-hide_banner', '-i', 'test_mix3.mp3', '-af', 'volumedetect', '-f', 'null', 'NUL']
        vol3 = subprocess.run(cmd_vol3, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in (vol3.stderr or '').split('\n'):
            if 'max_volume' in line or 'mean_volume' in line:
                print(f"  {line.strip()}")
else:
    print(f"Failed: {result3.stderr[-300:]}")

# TEST 4: BGM volume = 1.0 (full)
print("\n=== TEST 4: BGM volume = 1.0 (full) ===")
cmd_mix4 = [
    'ffmpeg', '-y',
    '-i', 'test_voice.mp3',
    '-stream_loop', '-1', '-i', 'test_bgm.mp3',
    '-filter_complex', '[0:a]volume=1.0[a0];[1:a]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]',
    '-map', '[aout]', '-c:a', 'libmp3lame', '-b:a', '192k', 'test_mix4.mp3'
]
result4 = subprocess.run(cmd_mix4, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if result4.returncode == 0:
    sz4 = os.path.getsize('test_mix4.mp3')
    print(f"Output: {sz4} bytes")
    if sz4 > 0:
        cmd_vol4 = ['ffmpeg', '-hide_banner', '-i', 'test_mix4.mp3', '-af', 'volumedetect', '-f', 'null', 'NUL']
        vol4 = subprocess.run(cmd_vol4, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in (vol4.stderr or '').split('\n'):
            if 'max_volume' in line or 'mean_volume' in line:
                print(f"  {line.strip()}")
else:
    print(f"Failed: {result4.stderr[-300:]}")

# Cleanup
for f in ['test_voice.mp3', 'test_bgm.mp3', 'test_mix.mp3', 'test_mix2.mp3', 'test_mix3.mp3', 'test_mix4.mp3']:
    if os.path.exists(f):
        os.remove(f)

print("\nDone!")
