import json

content = open("deepinfra_models.txt", encoding="utf-8").read()
# Skip the "Status: 200" first line
content = content[content.find("\n") + 1:]
data = json.loads(content)

models = [m.get("model_name", "") for m in data.get("data", [])]
print("Total models:", len(models))
for m in models:
    ml = m.lower()
    if any(k in ml for k in ["avatar", "image-to-video", "text-to-video", "talking", "sadtalker", "wav2lip", "animate", "video", "face", "lip"]):
        print(" -", m)