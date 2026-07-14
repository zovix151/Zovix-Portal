# Test the actual ffmpeg mixing command
import subprocess, os, json

# Create test audio files
print("Creating test audio files...")

# Create a 3-second voice track (sine tone at 440 Hz - like a beep)
cmd_voice = [
    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
    '-c:a', 'aac', '-b:a', '192k', 'test_voice.mp3'
]
subprocess.run(cmd_voice, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(f"Voice file size: {os.path.getsize('test_voice.mp3') if os.path.exists('test_voice.mp3') else 'NOT FOUND'}")

# Create a 10-second BGM track (sine tone at 220 Hz - different pitch)
cmd_bgm = [
    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=220:duration=10',
    '-c:a', 'aac', '-b:a', '192k', 'test_bgm.mp3'
]
subprocess.run(cmd_bgm, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(f"BGM file size: {os.path.getsize('test_bgm.mp3') if os.path.exists('test_bgm.mp3') else 'NOT FOUND'}")

# TEST 1: Current approach (stream_loop -1, amix duration=first)
print("\n=== TEST 1: Current approach (stream_loop -1 + amix) ===")
bgm_volume = 0.3
cmd1 = [
    'ffmpeg', '-y',
    '-i', 'test_voice.mp3',
    '-stream_loop', '-1', '-i', 'test_bgm.mp3',
    '-filter_complex', f'[0:a]volume=1.0[a0];[1:a]volume={bgm_volume:.2f}[a1];[a0][a1]amix=inputs=2:duration=first[aout]',
    '-map', '[aout]', '-c:a', 'aac', '-b:a', '192k', 'test_mix_current.mp3'
]
result1 = subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(f"Test 1 result: {'SUCCESS' if result1.returncode == 0 else 'FAILED'}")
print(f"stderr: {result1.stderr[:300]}")

# Check duration of mixed output
cmd_dur = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', 'test_mix_current.mp3']
dur = subprocess.run(cmd_dur, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(f"Mixed audio duration: {dur.stdout.strip()}s")

# TEST 2: Better approach - trim BGM to voice length, then mix
print("\n=== TEST 2: Trim BGM first, then mix ===")
cmd2 = [
    'ffmpeg', '-y',
    '-i', 'test_voice.mp3',
    '-i', 'test_bgm.mp3',
    '-filter_complex', 
    f'[1:a]volume={bgm_volume:.2f}[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]',
    '-map', '[aout]', '-c:a', 'aac', '-b:a', '192k', 'test_mix_trim.mp3'
]
result2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(f"Test 2 result: {'SUCCESS' if result2.returncode == 0 else 'FAILED'}")
dur2 = subprocess.run(cmd_dur, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(f"Mixed audio duration: {dur2.stdout.strip()}s")

# Let me check if the issue is that voice has no audio or BGM is silent
# Check voice audio with ffprobe
print("\n=== Voice audio analysis ===")
cmd_probe_voice = ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,channels,sample_rate', '-of', 'json', 'test_voice.mp3']
voice_info = subprocess.run(cmd_probe_voice, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(voice_info.stdout[:300])

print("\n=== BGM audio analysis ===")
cmd_probe_bgm = ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,channels,sample_rate', '-of', 'json', 'test_bgm.mp3']
bgm_info = subprocess.run(cmd_probe_bgm, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(bgm_info.stdout[:300])

# Try volume detect on mixed output
print("\n=== Volume analysis of mixed result ===")
cmd_vol = ['ffmpeg', '-hide_banner', '-i', 'test_mix_current.mp3', '-af', 'volumedetect', '-f', 'null', 'NUL']
vol_info = subprocess.run(cmd_vol, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print(vol_info.stderr[-300:] if vol_info.stderr else voL_info.stdout[-300:])

# Clean up
for f in ['test_voice.mp3', 'test_bgm.mp3', 'test_mix_current.mp3', 'test_mix_trim.mp3']:
    if os.path.exists(f):
        os.remove(f)

print("\nDone!")
