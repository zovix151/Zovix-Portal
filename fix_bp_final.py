import os
import uuid
import json
import random
import requests
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)

# ... (existing code) ...
def _generate_professional_blueprint_pil(prompt, blueprint_type="floor_plan", style="Modern", rooms_data=None):
    # ... (existing code) ...
    return output_path

def generate_blueprint(prompt, blueprint_type="floor_plan"):
    if os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY"):
        result = _generate_stability_blueprint(prompt, blueprint_type, "Modern")
        if result: return result
    result = _generate_pollinations_blueprint(prompt, blueprint_type, "Modern")
    if result: return result
    return _generate_professional_blueprint_pil(prompt, blueprint_type, "Modern")

def generate_blueprint_with_deepseek(prompt, blueprint_type="floor_plan", style="Modern"):
    # ... (existing code) ...
    return path
def generate_blueprint_from_data(blueprint_data, blueprint_type="floor_plan"):
    prompt = blueprint_data.get("description", blueprint_data.get("title", "Architectural Blueprint"))
    style = blueprint_data.get("style", "Modern")
    rooms = blueprint_data.get("rooms", [])
    return _generate_professional_blueprint_pil(prompt, blueprint_type, style, rooms)

def analyze_blueprint(blueprint_path):
    # ... (existing code) ...

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or get_system_secret("DEEPSEEK_API_KEY")
    if DEEPSEEK_API_KEY:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        sys_content = 'You are an expert architectural designer. Respond only with valid JSON.'
        bp_type_display = blueprint_type.replace("_", " ")
        user_content_lines = []
        user_content_lines.append(f"Generate a detailed {style} {bp_type_display} blueprint for: {prompt}")
        user_content_lines.append("")
        user_content_lines.append("Return ONLY valid JSON:")
        user_content_lines.append('{')
        user_content_lines.append('    "title": "Blueprint Title",')
        user_content_lines.append('    "description": "Detailed architectural description",')
        user_content_lines.append('    "rooms": ["Room1", "Room2", "Room3", ...],')
        user_content_lines.append('    "dimensions": "Total area sq ft",')
        user_content_lines.append(f'    "style": "{style}",')
        user_content_lines.append('    "structure_type": "Residential/Commercial",')
        user_content_lines.append('    "floor_count": 2,')
        user_content_lines.append('    "special_features": [],')
        user_content_lines.append('    "materials": ["brick", "concrete"],')
        user_content_lines.append('    "estimated_cost": "$XX,XXX"')
        user_content_lines.append('}')
        user_content = "\\n".join(user_content_lines)
        payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": sys_content}, {"role": "user", "content": user_content}], "temperature": 0.7, "max_tokens": 800, "response_format": {"type": "json_object"}}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                blueprint_data = json.loads(result['choices'][0]['message']['content'])
                st.session_state["deepseek_blueprint_data"] = blueprint_data
        except Exception as e:
            logger.warning(f"DeepSeek API failed: {e}")
    rooms_data = blueprint_data.get("rooms", []) if blueprint_data else None
    if os.getenv("STABILITY_API_KEY") or get_system_secret("STABILITY_API_KEY"):
        path = _generate_stability_blueprint(prompt, blueprint_type, style)
        if path: return path
    path = _generate_pollinations_blueprint(prompt, blueprint_type, style)
    if path: return path
    return _generate_professional_blueprint_pil(prompt, blueprint_type, style, rooms_data)

