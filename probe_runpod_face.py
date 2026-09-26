import os
import requests
from dotenv import dotenv_values

env = dotenv_values(r'c:\Zovix-Clean\.env')
key = (env.get('RUNPOD_API_KEY') or '').strip()
endpoint = (env.get('RUNPOD_ENDPOINT_FACE') or env.get('COMFYUI_FACE_RUNPOD_ENDPOINT_ID') or '').strip()
print('API_KEY_SET', bool(key))
print('ENDPOINT', endpoint or 'missing')

if not endpoint or not key:
    print('CONFIG_MISSING')
    raise SystemExit(0)

url = f'https://api.runpod.ai/v2/{endpoint}/health'
headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
try:
    r = requests.get(url, headers=headers, timeout=20)
    print('STATUS', r.status_code)
    print(r.text[:500])
except Exception as e:
    print('ERROR', type(e).__name__, str(e))
