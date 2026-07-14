c = open('engine.py', 'r', encoding='utf-8').read()

# Add a helper function near the top of engine.py (after imports)
# Find a good insertion point
insert_point = c.find("def parse_tagged_script")
if insert_point < 0:
    insert_point = c.find("class StitcherEngine")
    # Get before class
    class_start = insert_point
    insert_point = c.rfind('\n', 0, insert_point)
    insert_point = c.rfind('\n', 0, insert_point)

print(f'Insert point: {insert_point}')

# The helper dict
helper_dict = '''
# Voice name to ElevenLabs voice ID mapping (synced from app.py)
_ELEVENLABS_VOICE_ID_MAP = {
    "Adam (Premium Male)": "pNInz6obpgDQ5IdwJg7p",
    "Rachel (Premium Female)": "21m00Tcm4TlvDq8ikWAM",
    "Antoni (Premium Male)": "pNInz6obpgDQ5IdwJg7p",
    "Drew (Premium Male)": "21m00Tcm4TlvDq8ikWAM",
    "Josh (Premium Male)": "TxGEqnHWrfWFTfGW9XjX",
    "Arnold (Premium Male)": "nI5p1M2KqGjqV1zC3dDg",
    "Sam (Premium Male)": "yoZ06aMxZJJZCm3JXjX6",
    "Charlie (Premium Male)": "IKne3meq5aBk2K5JmR6s",
    "George (Premium Male)": "JwD6uI5q3x8p2LfzQn1g",
    "Emily (Premium Female)": "LcfcDJNUP1GQjkzn2xUj",
    "Grace (Premium Female)": "oWAxZDx7w5vj0W2pG8gB",
    "Olivia (Premium Female)": "nPczCjzI2devNBz1TQ9N",
    "Sophia (Premium Female)": "V7s9sP4p4GgK2q3zJ7fC",
    "Maya (Premium Female)": "lbQJzXb0QXB1Nq3vH6gK",
    "Lily (Premium Female)": "Y0lX1pYb3GkL8mRq4tNf",
    "Bella (Premium Female)": "EXAVITQu4vr2H2VjV4F7",
    "Aria (Premium Female)": "9BWtsMINqrJLrRacw9iw",
    "Ethan (Premium Male)": "g5CIjZEefAphodkY3ZLg",
    "Liam (Premium Male)": "l0z6i1s4jkQ0o2xV8cRg",
    "Noah (Premium Male)": "bIHdV24Gmz7JHK7Lh0fZ",
    "Oliver (Premium Male)": "L0yVHgHjzI2cV3mKq5Fg",
    "James (Premium Male)": "uBb6jQ1kL2pV3zG5x0Re",
    "Ava (Premium Female)": "cgSgspgA3M2e1qQ4n0Gd",
    "Isabella (Premium Female)": "Xr3s5fG2kL7pO0qV8cBf",
    "Mia (Premium Female)": "oF2gZ1hJ4kL9sQ7wE6rT",
    "Charlotte (Premium Female)": "gY6mQ1xL3kP0oZ8vW2cN",
}

def _resolve_cinematic_voice_id(voice_profile_name):
    """Resolve ElevenLabs voice ID from voice profile display name."""
    if not voice_profile_name:
        return "pNInz6obpgDQ5IdwJg7p"  # default Rachel
    
    # Direct lookup
    if voice_profile_name in _ELEVENLABS_VOICE_ID_MAP:
        return _ELEVENLABS_VOICE_ID_MAP[voice_profile_name]
    
    # Partial match (e.g. 'Drew' -> 'Drew (Premium Male)')
    for name, vid in _ELEVENLABS_VOICE_ID_MAP.items():
        if voice_profile_name.lower() in name.lower() or name.lower() in voice_profile_name.lower():
            return vid
    
    return "pNInz6obpgDQ5IdwJg7p"  # default

'''

c = c[:insert_point] + helper_dict + c[insert_point:]

with open('engine.py', 'w', encoding='utf-8') as f:
    f.write(c)

try:
    compile(c, 'engine.py', 'exec')
    print("✅ Syntax check PASSED!")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
