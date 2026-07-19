# This script replaces the old generate_drawing_hybrid in app.py
# with the new DrawEngine-based implementation

import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find function start
func_start = content.find('def generate_drawing_hybrid(prompt')
print(f"Function start at: {func_start}")

if func_start >= 0:
    # Find end - next def/class/=== line
    rest = content[func_start+100:]
    matches = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest, re.MULTILINE))
    if matches:
        func_end = func_start + 100 + matches[0].start()
        print(f"Function ends at: {func_end}")
        
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

        new_content = content[:func_start] + new_func + content[func_end:]
        
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"SUCCESS! Replaced {func_end - func_start} chars with {len(new_func)} chars")
    else:
        print("Could not find function end")
else:
    print("Function not found!")
