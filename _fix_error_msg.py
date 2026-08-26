import io

path = "app.py"
with io.open(path, "r", encoding="utf-8", newline="") as f:
    content = f.read()

old = (
    "        if not engine.is_available():\n"
    '            logger.warning("[DeepInfra] Engine/API key not available - falling back to local Wav2Lip")\n'
    "            return _run_local_wav2lip_fallback(prompt, face_image_path, duration, quality)"
)

new = (
    "        if not engine.is_available():\n"
    '            msg = "DeepInfra API key not configured. Face Studio ko DeepInfra Cloud pe generate karne ke liye .streamlit/secrets.toml me DEEPINFRA_API_KEY set karein."\n'
    '            try:\n'
    '                st.session_state["replicate_last_error"] = msg\n'
    "            except Exception:\n"
    "                pass\n"
    '            logger.warning("[DeepInfra] Engine/API key not available - falling back to local Wav2Lip")\n'
    "            return _run_local_wav2lip_fallback(prompt, face_image_path, duration, quality)"
)

count = content.count(old)
print("occurrences:", count)
if count >= 1:
    content = content.replace(old, new, 1)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print("REPLACED OK")
else:
    print("NO MATCH - dumping lines around 'engine.is_available'")
    lines = content.split("\n")
    for idx, ln in enumerate(lines):
        if "engine.is_available" in ln:
            print(idx+1, repr(ln))
