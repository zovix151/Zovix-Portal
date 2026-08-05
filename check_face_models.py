import requests

key = "gHxCwgE86zutKxGotwunc8BUcOiMUzDu"
r = requests.get("https://api.deepinfra.com/v1/models", headers={"Authorization": "Bearer " + key}, timeout=30)
print("Status:", r.status_code)
with open("deepinfra_models.txt", "w", encoding="utf-8") as f:
    f.write("Status: " + str(r.status_code) + "\n" + r.text)
print("Saved to deepinfra_models.txt")