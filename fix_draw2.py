import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_start = 'def generate_drawing_hybrid(prompt, style="realistic", canvas_size=(1024, 768), engine="Auto (Pollinations \u2192 Gemini \u2192 Fallback)", quality="Standard"):'
old_end = '    return generate_enhanced_fallback_drawing(prompt, style, canvas_size)'

func_start = content.find(old_start)
if func_start < 0:
    print(f"ERROR: Could not find start string!")
    # Try to find without unicode
    func_start = content.find('def generate_drawing_hybrid(prompt')
    print(f"Found at {func_start}")
    # Print around it
    print(repr(content[func_start:func_start+150]))

func_end = content.find(old_end, func_start)
if func_end < 0:
    print(f"ERROR: Could not find end string!")
    # Find last occurrence of return
    rest = content[func_start:]
    matches = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest[100:], re.MULTILINE))
    end = func_start + 100 + matches[0].start()
    print(f"Using regex end at {end}")
    func_end = end
else:
    func_end = func_end + len(old_end)
    print(f"Found end at {func_end}")

old_func = content[func_start:func_end]
print(f"Old function: {func_start} to {func_end} = {func_end - func_start} chars")

new_func = '''def generate_drawing_hybrid(prompt, style="realistic", canvas_size=(1024, 768), engine="Auto (Pollinations \u2192 Gemini \u2192 Fallback)", quality="Standard"):
    """
    WORLD-CLASS DRAW GENERATOR - 6-Tier Cascade
    Delegates to engine.py's DrawEngine for multi-provider support
    """
    from engine import DrawEngine
    
    # Map old engine names to new engine_filter
    engine_map = {
        "Auto (Pollinations \u2192 Gemini \u2192 Fallback)": "Auto",
        "Pollinations.ai (Free + Fast)": "Pollinations",
        "Gemini Flash (Premium + Quality)": "Gemini",
        "Stability AI (Highest Quality)": "Stability",
        "Replicate Flux (Fast SD)": "Replicate",
        "Hugging Face (FLUX.1)": "HuggingFace",
        "Fallback Only (100% Local)": "Fallback",
    }
    engine_filter = engine_map.get(engine, "Auto")
    
    if engine_filter == "Fallback":
        return DrawEngine.generate_fallback_only(prompt, style, canvas_size)
    else:
        return DrawEngine.generate(prompt, style, canvas_size, engine_filter, quality)'''

new_content = content[:func_start] + new_func + content[func_end:]
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f"Replaced successfully! New function length: {len(new_func)}")
print("Done!")
