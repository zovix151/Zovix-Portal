import json
import urllib.request
import uuid

server_address = "etpdh884qrttuj-8188.proxy.runpod.net"
client_id = str(uuid.uuid4())

with open("zovix_workflow.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# Agar workflow nested format me hai toh usko correct API prompt dict me extract kar rahe hain
workflow_data = raw_data.get("output", raw_data)
if "prompt" in workflow_data:
    workflow_data = workflow_data["prompt"]

def queue_prompt(prompt_data):
    payload = {"prompt": prompt_data, "client_id": client_id}
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(
        f"https://{server_address}/prompt", 
        data=data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read())
    except urllib.error.HTTPError as e:
        print("Server returned error body:", e.read().decode('utf-8'))
        raise e

try:
    result = queue_prompt(workflow_data)
    print("Success! Prompt Queued, ID:", result.get('prompt_id'))
except Exception as e:
    print("Execution Failed:", e)