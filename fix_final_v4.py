"""FINAL FIX v4 - Move function to end of file, keep routing chain intact"""
import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. EXTRACT the ENTIRE function (def + all its content)
func_start = c.find('def run_production_engine_mode()')
# Find the function end: just before the orphan elif
orphan_elif = c.find('elif st.session_state["studio_active_mode"] == "Production Engine"', func_start)
print(f'Function def at: {func_start}')
print(f'Ophan elif at: {orphan_elif}')

# The function content is from func_start to orphan_elif-1 (exclude blank lines between)
# But wait - we already removed the orphan else so it's at the right place? NO!
# Let's find the actual construction

# Check what's directly between function and the "elif Production Engine"
between = c[func_start:orphan_elif]
between_lines = between.split('\n')
print(f'Lines between func def and orphan elif: {len(between_lines)}')
print(f'Last 3 lines:')
for l in between_lines[-3:]:
    sp = len(l) - len(l.lstrip())
    print(f'  [{sp}sp] {l[:80]}')

# The function content ends at orphan_elif but let's verify
# What comes at the start of the function after def?
func_body_start = func_start + len('def run_production_engine_mode():\n')
func_body_first = c[func_body_start:func_body_start+80]
print(f'\nFirst line after def: {repr(func_body_first)}')

# Actually let me check: was the orphan elif already removed?
# Count the routing lines
for m in re.finditer(r'elif st.session_state\["studio_active_mode"\].*', c):
    line = m.group()
    sp = len(line) - len(line.lstrip())
    print(f'  [{sp}sp] {line[:70]}')
