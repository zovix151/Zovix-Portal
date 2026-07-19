# Sync emotion voice to _live_emotion_section.txt and app_backup_before_6fixes.py
import re

# Read the new function from app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

func_start = app_content.find('def generate_emotion_voice(')
rest = app_content[func_start+50:]
matches = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest, re.MULTILINE))
func_end = func_start + 50 + matches[0].start()
new_func = app_content[func_start:func_end]

# Fix _live_emotion_section.txt
with open('_live_emotion_section.txt', 'r', encoding='utf-8') as f:
    text_content = f.read()

# Replace render_live_emotion_voice function
func_start_t = text_content.find('def render_live_emotion_voice()')
if func_start_t >= 0:
    rest_t = text_content[func_start_t+50:]
    matches_t = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest_t, re.MULTILINE))
    if matches_t:
        func_end_t = func_start_t + 50 + matches_t[0].start()
        # Get new render from app.py
        app_render_start = app_content.find('def render_live_emotion_voice()')
        if app_render_start >= 0:
            rest_ar = app_content[app_render_start+50:]
            matches_ar = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest_ar, re.MULTILINE))
            if matches_ar:
                app_render_end = app_render_start + 50 + matches_ar[0].start()
                new_render = app_content[app_render_start:app_render_end]
                text_content = text_content[:func_start_t] + new_render + text_content[func_end_t:]
                
                # Now replace generate function
                gen_start = text_content.find('def generate_emotion_voice(')
                if gen_start >= 0:
                    rest_gen = text_content[gen_start+50:]
                    matches_gen = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest_gen, re.MULTILINE))
                    if matches_gen:
                        gen_end = gen_start + 50 + matches_gen[0].start()
                        text_content = text_content[:gen_start] + new_func + text_content[gen_end:]
                        with open('_live_emotion_section.txt', 'w', encoding='utf-8') as f:
                            f.write(text_content)
                        print('_live_emotion_section.txt: Replaced both functions OK')

# Fix app_backup_before_6fixes.py
with open('app_backup_before_6fixes.py', 'r', encoding='utf-8') as f:
    backup_content = f.read()

for func_name in ['def render_live_emotion_voice()', 'def generate_emotion_voice(']:
    func_start_b = backup_content.find(func_name)
    if func_start_b >= 0:
        rest_b = backup_content[func_start_b+50:]
        matches_b = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest_b, re.MULTILINE))
        if matches_b:
            func_end_b = func_start_b + 50 + matches_b[0].start()
            app_start = app_content.find(func_name)
            if app_start >= 0:
                rest_ap = app_content[app_start+50:]
                matches_ap = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest_ap, re.MULTILINE))
                if matches_ap:
                    app_end = app_start + 50 + matches_ap[0].start()
                    new_fn = app_content[app_start:app_end]
                    backup_content = backup_content[:func_start_b] + new_fn + backup_content[func_end_b:]
                    print(f'app_backup_before_6fixes.py: Replaced {func_name}')

with open('app_backup_before_6fixes.py', 'w', encoding='utf-8') as f:
    f.write(backup_content)

print('All files synced!')
