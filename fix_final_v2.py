"""
FINAL FIX: Rebuild the function and routing correctly.
"""
import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Find ALL occurrences of Production Engine routing
count = c.count('Production Engine')
print(f'Found {count} occurrences of "Production Engine"')

# Find function definition
func_idx = c.find('def run_production_engine_mode()')
print(f'Function def at {func_idx}')

# Find all elif/if references to Production Engine
import re as _re
for m in _re.finditer(r'.*?Production Engine.*?(?:\n|$)', c):
    line = m.group().strip()
    if line:
        print(f'  Found: {repr(line[:100])}')

# Find the end of the function (where does it actually end?)
# The function body starts with st.markdown at 4 spaces indent
# It ends where indent returns to 0 (function scope)
# But with the routing code embedded, it never returns to 0

# Let me check what's between the function def and the first "elif ... Draw Mode" AFTER it
rest = c[func_idx:]
draw_idx = rest.find('elif st.session_state["studio_active_mode"] == "Draw Mode"')
print(f'\nDistance from func to Draw Mode: {draw_idx}')

# Find the function's last statement
func_body = rest[:draw_idx]
lines = func_body.split('\n')
# Last non-empty non-comment line
for i in range(len(lines)-1, -1, -1):
    s = lines[i].strip()
    if s and not s.startswith('#') and not s.startswith('"') and not s.startswith("'"):
        sp = len(lines[i]) - len(lines[i].lstrip())
        print(f'Last content line ({i}): [{sp}sp] {repr(s[:80])}')
        break
