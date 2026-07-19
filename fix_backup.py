import re

# Fix draw_hybrid.txt
with open('draw_hybrid.txt', 'r', encoding='utf-8') as f:
    content = f.read()

func_start = content.find('def generate_drawing_hybrid(prompt')
if func_start >= 0:
    rest = content[func_start+100:]
    matches = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest, re.MULTILINE))
    if matches:
        func_end = func_start + 100 + matches[0].start()
        new_func = '''def generate_drawing_hybrid(prompt, style="realistic", canvas_size=(1024, 768), engine="Auto (Pollinations \\u2192 Gemini \\u2192 Fallback)", quality="Standard"):
    """
    WORLD-CLASS DRAW GENERATOR - 6-Tier Cascade
    Delegates to engine.py's DrawEngine for multi-provider support
    """
    from engine import DrawEngine
    
    engine_map = {
        "Auto (Pollinations \\u2192 Gemini \\u2192 Fallback)": "Auto",
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
        content = content[:func_start] + new_func + content[func_end:]
        with open('draw_hybrid.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"draw_hybrid.txt: Replaced OK")

# Fix app_backup_before_6fixes.py
with open('app_backup_before_6fixes.py', 'r', encoding='utf-8') as f:
    content = f.read()

func_start = content.find('def generate_drawing_hybrid(prompt')
if func_start >= 0:
    rest = content[func_start+100:]
    matches = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest, re.MULTILINE))
    if matches:
        func_end = func_start + 100 + matches[0].start()
        new_func = '''def generate_drawing_hybrid(prompt, style="realistic", canvas_size=(1024, 768), engine="Auto (Pollinations \\u2192 Gemini \\u2192 Fallback)", quality="Standard"):
    """
    WORLD-CLASS DRAW GENERATOR - 6-Tier Cascade
    Delegates to engine.py's DrawEngine for multi-provider support
    """
    from engine import DrawEngine
    
    engine_map = {
        "Auto (Pollinations \\u2192 Gemini \\u2192 Fallback)": "Auto",
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
        content = content[:func_start] + new_func + content[func_end:]
        with open('app_backup_before_6fixes.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"app_backup_before_6fixes.py: Replaced OK")

print("All files updated!")
