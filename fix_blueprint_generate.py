#!/usr/bin/env python3
"""Fix: Add generate_blueprint() function + prompt-based room detection + runtime globals() lookup"""
import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix run_blueprints_mode - use globals() for runtime lookup
# Find the exact call site
old_call = "                                    _temp_bp_func = generate_blueprint_with_deepseek"
new_call = "                                    _temp_bp_func = globals()['generate_blueprint_with_deepseek']"

if old_call in content:
    content = content.replace(old_call, new_call)
    print("1. Fixed globals() lookup for generate_blueprint_with_deepseek")
else:
    # Try alternative patterns
    for patt in ["generate_blueprint_with_deepseek", "_temp_bp_func = generate_blueprint_with_deepseek"]:
        parts = content.split(patt)
        if len(parts) > 2:
            print(f"Multiple occurrences of {patt}: {len(parts)-1}")
    print("1. Could not find exact match, trying different approach...")

# 2. Add generate_blueprint function with prompt-based room detection right before generate_blueprint_smart
insert_point = content.find("def generate_blueprint_smart")
if insert_point >= 0:
    new_func = '''def generate_blueprint(prompt, blueprint_type="floor_plan"):
    """PROMPT-AWARE Blueprint Generator - Detects rooms from prompt"""
    # Detect rooms from prompt
    prompt_lower = prompt.lower()
    room_keywords = [
        ("Living Room", ["living", "lounge", "family room"]),
        ("Kitchen", ["kitchen", "cooking"]),
        ("Master Bedroom", ["master bedroom", "master bed"]),
        ("Bedroom", ["bedroom", "bed room"]),
        ("Bathroom", ["bathroom", "bath", "washroom", "toilet"]),
        ("Dining Room", ["dining"]),
        ("Study", ["study", "office", "library"]),
        ("Balcony", ["balcony", "terrace", "deck"]),
        ("Garage", ["garage", "parking"]),
        ("Garden", ["garden", "lawn", "yard"]),
        ("Hallway", ["hallway", "corridor"]),
        ("Store Room", ["store", "storage", "pantry"]),
        ("Prayer Room", ["prayer", "pooja", "mandir"]),
        ("Playroom", ["play", "game"]),
        ("Laundry", ["laundry", "washing"]),
    ]
    detected_rooms = []
    for room_name, keywords in room_keywords:
        if any(kw in prompt_lower for kw in keywords):
            if room_name not in detected_rooms:
                detected_rooms.append(room_name)
    if not detected_rooms:
        # Count rooms mentioned with numbers
        import re as _re
        room_count = 0
        for match in _re.finditer(r'(\\d+)\\s*(?:bhk|bedroom|room|floor|storey)', prompt_lower):
            room_count = max(room_count, int(match.group(1)))
        if room_count > 0:
            detected_rooms = ["Living Room", "Kitchen"]
            for i in range(1, room_count + 1):
                detected_rooms.append(f"Bedroom {i}")
            detected_rooms.append("Bathroom")
        else:
            # Check for building type keywords
            if any(w in prompt_lower for w in ["office", "commercial", "shop"]):
                detected_rooms = ["Reception", "Cabin", "Meeting Room", "Workspace", "Pantry"]
            elif any(w in prompt_lower for w in ["restaurant", "cafe", "hotel"]):
                detected_rooms = ["Dining Area", "Kitchen", "Bar", "Storage", "Washroom"]
            elif any(w in prompt_lower for w in ["school", "college", "university"]):
                detected_rooms = ["Classroom", "Library", "Lab", "Office", "Hall"]
            elif any(w in prompt_lower for w in ["hospital", "clinic"]):
                detected_rooms = ["Ward", "OPD", "Pharmacy", "Lab", "Office"]
            else:
                detected_rooms = ["Living Room", "Kitchen", "Master Bedroom", "Bedroom 2", "Bathroom"]
    
    return generate_world_class_blueprint(prompt, blueprint_type, "Modern")


'''
    content = content[:insert_point] + new_func + content[insert_point:]
    print(f"2. Added generate_blueprint() function with prompt-based room detection ({len(new_func)} chars)")
else:
    print("2. Could not find generate_blueprint_smart - searching...")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
