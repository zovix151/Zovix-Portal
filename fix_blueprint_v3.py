import os
import json
import uuid
import random
import requests
from PIL import Image, ImageDraw
import logging
import re

logger = logging.getLogger(__name__)

# ... existing code ...
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        
        prompt_for_ds = f'You are a world-class architectural designer. Generate a detailed {style} {blueprint_type.replace("_", " ")} blueprint for: {prompt}'

        system_prompt = prompt_for_ds + '''

Return ONLY valid JSON (no markdown):
{
    "title": "Descriptive blueprint title",
    "description": "Detailed architectural description with style notes",
    "rooms": ["Living Room", "Kitchen", ...],
    "dimensions": "Total area with sq ft",
    "style": "''' + style + '''",
    "structure_type": "Residential/Commercial/Industrial/Educational",
    "floor_count": 2,
    "special_features": ["open kitchen", "walk-in closet", "terrace"],
    "materials": ["brick", "concrete", "glass", "wood"],
    "estimated_cost": "$XX,XXX - $XX,XXX"
}'''

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are an expert architectural designer. Respond only with valid JSON."},
                {"role": "user", "content": system_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 800,
            "response_format": {"type": "json_object"}
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                blueprint_data = json.loads(result['choices'][0]['message']['content'])
                st.session_state["deepseek_blueprint_data"] = blueprint_data
                logger.info(f"DeepSeek blueprint generated: {blueprint_data.get('title', 'N/A')}")
        except Exception as e:
            logger.warning(f"DeepSeek API failed: {e}")
    
// ... rest of code ...

