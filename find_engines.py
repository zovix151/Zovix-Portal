c = open('app.py','r',encoding='utf-8').read()

# Find each engine function def and its size
import re
for func_name in ['run_cinematic_engine', 'run_creative_workshop', 'run_blueprints_mode', 'run_upscaler_mode', 'run_draw_mode', 'run_video_editor_mode', 'run_unified_face_video_mode', 'generate_dynamic_ui']:
    pattern = 'def ' + func_name + '('
    idx = c.find(pattern)
    if idx >= 0:
        # Find the function body - go to next def at same level
        next_def = c.find('\ndef ', idx+len(pattern))
        if next_def < 0:
            next_def = len(c)
        print(f'{func_name}: {next_def - idx} chars (from {idx} to {next_def})')
