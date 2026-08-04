#!/usr/bin/env python3
"""Fix Blueprint Engine - Direct app.py modification"""
import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove old function definitions + their bodies
# Find each old function and its end
old_funcs = [
    'def generate_blueprint(prompt, blueprint_type="floor_plan"):',
    'def generate_blueprint_with_deepseek(prompt, blueprint_type="floor_plan", style="Modern"):',
    'def generate_blueprint_from_data(blueprint_data, blueprint_type="floor_plan"):',
    'def analyze_blueprint(blueprint_path):',
]

for old_func in old_funcs:
    idx = content.find(old_func)
    if idx >= 0:
        rest = content[idx+100:]
        match = re.search(r'(?<=\n)(?:def |class |# ={3,})', rest)
        if match:
            end = idx + 100 + match.start()
            content = content[:idx] + content[end:]

# Add new code at end with proper escaping
new_code = '''

# ========================================================
# WORLD-CLASS BLUEPRINT ENGINE - DeepSeek AI + Stability AI + PIL Pro
# ========================================================

BLUEPRINT_COLOR_PALETTE = {
    "Modern": [(30, 60, 150), (45, 80, 180), (60, 140, 220), (100, 180, 255), (200, 220, 255)],
    "Classic": [(30, 40, 80), (50, 60, 120), (70, 90, 150), (120, 140, 180), (200, 200, 220)],
    "Minimalist": [(40, 40, 45), (80, 80, 85), (140, 140, 145), (200, 200, 200), (230, 230, 235)],
    "Industrial": [(60, 50, 40), (100, 85, 70), (150, 130, 110), (180, 160, 140), (220, 200, 180)],
    "Traditional": [(40, 55, 90), (60, 80, 120), (90, 115, 155), (130, 155, 185), (200, 210, 225)]
}

def _generate_smart_room_layout(rooms, width, height, style="Modern"):
    """Generate professional room layout with smart grid"""
    num_rooms = len(rooms)
    margin = 40
    header_h = 80
    usable_w = width - 2 * margin
    usable_h = height - margin - header_h - 60
    grid_cols = min(max(2, int(num_rooms ** 0.5) + (1 if num_rooms > 4 else 0)), 4)
    grid_rows = (num_rooms + grid_cols - 1) // grid_cols
    cell_w = usable_w // grid_cols
    cell_h = usable_h // grid_rows
    positions = []
    colors = BLUEPRINT_COLOR_PALETTE.get(style, BLUEPRINT_COLOR_PALETTE["Modern"])
    for i in range(num_rooms):
        col = i % grid_cols
        row = i // grid_cols
        x1 = margin + col * cell_w
        y1 = header_h + row * cell_h
        x2 = x1 + cell_w - 20
        y2 = y1 + cell_h - 20
        color = colors[i % len(colors)]
        positions.append((x1, y1, x2, y2, color, rooms[i]))
    return positions

def _generate_stability_blueprint(prompt, blueprint_type="floor_plan", style="Modern"):
    """Tier 1: Stability AI Blueprint Generator"""
    api_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
    if not api_key or api_key == "mock" or len(api_key.strip()) < 5:
        return None
    try:
        bp_type_display = blueprint_type.replace("_", " ")
        enhanced = f"Professional architectural {style} {bp_type_display} drawing, {prompt}, blueprint style, technical drawing, grid paper"
        url = "https://api.stability.ai/v2beta/stable-image/generate/core"
        headers = {"authorization": f"Bearer {api_key}", "accept": "image/*"}
        files = {"prompt": (None, enhanced), "output_format": (None, "png"), "aspect_ratio": (None, "16:9"), "style_preset": (None, "architectural-interior")}
        resp = requests.post(url, headers=headers, files=files, timeout=45)
        if resp.status_code == 200 and len(resp.content) > 10000:
            fname = f"blueprints/blueprint_{uuid.uuid4().hex[:8]}.png"
            os.makedirs("blueprints", exist_ok=True)
            with open(fname, "wb") as f:
                f.write(resp.content)
            return fname
    except Exception as e:
        logger.warning(f"Stability Blueprint failed: {e}")
    return None

def _generate_pollinations_blueprint(prompt, blueprint_type="floor_plan", style="Modern"):
    """Tier 2: Pollinations Blueprint Generator"""
    try:
        bp_type_display = blueprint_type.replace("_", " ")
        enhanced = f"architectural {bp_type_display}, {style}, {prompt}, blueprint, technical drawing, grid"
        import urllib.parse
        encoded = urllib.parse.quote(enhanced)
        seed = random.randint(1, 999999)
        url = f"https://image.pollinations.ai/p/{encoded}?width=1200&height=800&seed={seed}&nologo=true"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "image/*"}
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 5000:
            fname = f"blueprints/blueprint_{uuid.uuid4().hex[:8]}.png"
            os.makedirs("blueprints", exist_ok=True)
            with open(fname, "wb") as f:
                f.write(resp.content)
            return fname
    except Exception as e:
        logger.warning(f"Pollinations Blueprint failed: {e}")
    return None

def _generate_professional_blueprint_pil(prompt, blueprint_type="floor_plan", style="Modern", rooms_data=None):
    """Tier 3: Professional PIL Blueprint Generator - Always Works"""
    width, height = 1400, 1000
    img = Image.new("RGB", (width, height), color=(235, 238, 250))
    draw = ImageDraw.Draw(img)
    
    # Blueprint grid
    for x in range(0, width, 30):
        draw.line([(x, 0), (x, height)], fill=(200, 208, 230), width=1)
    for y in range(0, height, 30):
        draw.line([(0, y), (width, y)], fill=(200, 208, 230), width=1)
    for x in range(0, width, 150):
        draw.line([(x, 0), (x, height)], fill=(180, 190, 220), width=1)
    for y in range(0, height, 150):
        draw.line([(0, y), (width, y)], fill=(180, 190, 220), width=1)
    
    colors = BLUEPRINT_COLOR_PALETTE.get(style, BLUEPRINT_COLOR_PALETTE["Modern"])
    draw.rectangle([(20, 20), (width-20, height-20)], outline=colors[0], width=4)
    
    if rooms_data:
        rooms = rooms_data[:8]
    else:
        rooms = ["Living Room", "Kitchen", "Master Bedroom", "Bedroom 2", "Bathroom"]
    
    room_positions = _generate_smart_room_layout(rooms, width, height, style)
    for i, (x1, y1, x2, y2, color, room_name) in enumerate(room_positions):
        draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
        door_x = x1 + (x2 - x1) // 2
        draw.arc([(door_x - 15, y1 - 5), (door_x + 15, y1 + 25)], start=0, end=180, fill=color, width=3)
        draw.text(((x1+x2)//2 - len(room_name)*5, (y1+y2)//2 - 15), room_name[:15], fill=color)
        room_w = x2 - x1
        room_h = y2 - y1
        dim_text = f"{room_w//10}'x{room_h//10}'"
        draw.text(((x1+x2)//2 - len(dim_text)*4, (y1+y2)//2 + 8), dim_text, fill=(100, 120, 180))
    
    # Title block
    draw.rectangle([(width-450, height-130), (width-20, height-20)], fill=(220, 225, 245), outline=colors[0], width=2)
    draw.text((width-440, height-120), "PROJECT", fill=colors[0])
    bp_title = f"{style} {blueprint_type.replace('_', ' ').title()}"
    draw.text((width-440, height-100), f": {bp_title}", fill=(40, 50, 100))
    draw.text((width-440, height-80), "STYLE", fill=colors[0])
    draw.text((width-440, height-60), f": {style}", fill=(40, 50, 100))
    draw.text((width-440, height-40), f"ROOMS: {len(rooms)}", fill=(40, 50, 100))
    
    # Scale bar
    for i in range(5):
        seg_x = 50 + i * 40
        seg_color = colors[0] if i % 2 == 0 else (255, 255, 255)
        draw.rectangle([(seg_x, height-55), (seg_x+20, height-40)], fill=seg_color)
    
    # North arrow
    draw.polygon([(width-480, 30), (width-490, 60), (width-470, 60)], fill=colors[0])
    draw.text((width-483, 62), "N", fill=colors[0])
    
    title_stub = style[:15].replace(" ", "_")
    fname = f"blueprints/bp_{title_stub}_{uuid.uuid4().hex[:4]}.png"
    os.makedirs("blueprints", exist_ok=True)
    img.save(fname, quality=95)
    return fname

def generate_blueprint(prompt, blueprint_type="floor_plan"):
    """WORLD-CLASS Blueprint Generator - 3-Tier Cascade"""
    api_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
    if api_key and api_key != "mock" and len(api_key.strip()) >= 5:
        result = _generate_stability_blueprint(prompt, blueprint_type)
        if result:
            return result
    result = _generate_pollinations_blueprint(prompt, blueprint_type)
    if result:
        return result
    return _generate_professional_blueprint_pil(prompt, blueprint_type)

def generate_blueprint_with_deepseek(prompt, blueprint_type="floor_plan", style="Modern"):
    """DeepSeek AI Enhanced Blueprint Generator"""
    blueprint_data = None
    if DEEPSEEK_API_KEY:
        bp_type = blueprint_type.replace("_", " ")
        user_msg = f"Generate {style} {bp_type} blueprint for: {prompt}"
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are an expert architectural designer. Respond only with valid JSON."},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.7,
            "max_tokens": 800,
            "response_format": {"type": "json_object"}
        }
        try:
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                blueprint_data = json.loads(result["choices"][0]["message"]["content"])
                st.session_state["deepseek_blueprint_data"] = blueprint_data
        except Exception as e:
            logger.warning(f"DeepSeek API failed: {e}")
    
    rooms_data = blueprint_data.get("rooms", []) if blueprint_data else None
    
    api_key = os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY")
    if api_key and api_key != "mock" and len(api_key.strip()) >= 5:
        path = _generate_stability_blueprint(prompt, blueprint_type, style)
        if path:
            return path
    path = _generate_pollinations_blueprint(prompt, blueprint_type, style)
    if path:
        return path
    return _generate_professional_blueprint_pil(prompt, blueprint_type, style, rooms_data)

def generate_blueprint_from_data(blueprint_data, blueprint_type="floor_plan"):
    prompt = blueprint_data.get("description", blueprint_data.get("title", "Blueprint"))
    style = blueprint_data.get("style", "Modern")
    rooms = blueprint_data.get("rooms", [])
    return _generate_professional_blueprint_pil(prompt, blueprint_type, style, rooms)

def analyze_blueprint(blueprint_path):
    if not blueprint_path or not os.path.exists(blueprint_path):
        return {"format": "N/A", "width": "N/A", "height": "N/A", "estimated_rooms": "N/A", "total_area": "N/A", "structure_type": "N/A", "confidence_score": 0.0, "style_detected": "N/A", "complexity": "N/A"}
    try:
        img = Image.open(blueprint_path)
        width, height = img.size
        gray = img.convert("L")
        pixels = list(gray.getdata())
        if pixels:
            avg = sum(pixels) / len(pixels)
            std = (sum((p - avg) ** 2 for p in pixels) / len(pixels)) ** 0.5
        else:
            std = 0
        complexity = "Low"
        if std > 80:
            complexity = "High"
        elif std > 50:
            complexity = "Medium"
        num_regions = max(1, int(width * height / 50000))
        filename = os.path.basename(blueprint_path).lower()
        structure_type = "Residential"
        if "commercial" in filename:
            structure_type = "Commercial"
        elif "industrial" in filename:
            structure_type = "Industrial"
        estimated_area = f"{num_regions * 300}+ sq ft"
        confidence = min(0.9, 0.5 + std / 200)
        return {"format": img.format or "PNG", "width": width, "height": height, "estimated_rooms": str(num_regions), "total_area": estimated_area, "structure_type": structure_type, "confidence_score": round(confidence, 2), "style_detected": "Modern", "complexity": complexity}
    except Exception as e:
        logger.warning(f"Blueprint analysis error: {e}")
        return {"format": "Unknown", "width": "N/A", "height": "N/A", "estimated_rooms": "N/A", "total_area": "N/A", "structure_type": "N/A", "confidence_score": 0.0, "style_detected": "N/A", "complexity": "N/A"}
'''

content = content + new_code

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Done! Wrote {len(new_code)} chars of new blueprint code.")
