"""FINAL FIX - proper approach"""
import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

func_idx = c.find('def run_production_engine_mode()')

# Find what's at line 184 and around
rest = c[func_idx+100:]
lines = rest.split('\n')

for i in range(183, 188):
    sp = len(lines[i]) - len(lines[i].lstrip())
    clean = re.sub(r'[^\x20-\x7E]', '?', lines[i])
    print(f'{i}: [{sp}sp] {clean[:90]}')

# Now let's check the actual function scope
# The function body is defined with indent 4 spaces
# ALL content should be at >= 4 spaces
# But there are lines at 0 and 8 spaces coming from the orphan elif

# Actually the issue is remove of orphan failed because there are MULTIPLE instances
print(f'\n"elif ... Production Engine" count: {c.count("elif st.session_state")}')
for m in re.finditer(r'elif st.session_state\["studio_active_mode"\].*?(?:\n|$)', c):
    print(f'  At {m.start()}: {repr(m.group().strip()[:100])}')
