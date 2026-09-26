import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path('c:/Zovix-Clean/.env'))

from comfyui_engine import generate_face_video

face = r'c:\Zovix-Clean\LivePortrait\assets\examples\source\s0.jpg'
audio = r'c:\Zovix-Clean\assets\music\default.mp3'

print('RUNPOD_API_KEY_SET', bool(os.getenv('RUNPOD_API_KEY', '')))
print('RUNPOD_ENDPOINT_FACE', os.getenv('RUNPOD_ENDPOINT_FACE', ''))
print('RUNPOD_FACE_MODE', os.getenv('RUNPOD_FACE_MODE', ''))
print('FACE_EXISTS', os.path.exists(face))
print('AUDIO_EXISTS', os.path.exists(audio))

result = generate_face_video(
    face_image_path=face,
    audio_path=audio,
    script_text='Hello, welcome to Zovix. This is a test video.',
    duration=8,
    quality='HD',
    timeout=300,
)

print('RESULT_TYPE', type(result).__name__)
print('RESULT', result)
if result and os.path.exists(result):
    print('FILE_SIZE', os.path.getsize(result))
