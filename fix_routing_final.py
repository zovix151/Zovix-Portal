"""
FIX: Properly close run_production_engine_mode function and fix routing
"""
import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Find the orphan elif and its surrounding context
orphan = 'elif st.session_state["studio_active_mode"] == "Production Engine"'
orphan_idx = c.find(orphan)

# Find the function start
func_idx = c.find('def run_production_engine_mode()')

# Find Draw Mode routing (real main chain)
draw = '\n    elif st.session_state["studio_active_mode"] == "Draw Mode"'
draw_idx = c.find(draw, func_idx + 1000)

print(f'Function at {func_idx}')
print(f'Orphan elif at {orphan_idx}')
print(f'Draw Mode routing at {draw_idx}')

# The orphan elif + run_production_engine_mode() is the EXACT routing we need
# We need to:
# 1. Find the main routing chain's last elif 
# 2. Insert the Production Engine route between Upscaler Mode and Draw Mode  
# 3. Remove the orphan from inside the function
# 4. Close the function

# First, remove the orphan elif block from inside the function area
orphan_block = c[orphan_idx:draw_idx]
print(f'\nOrphan block length: {len(orphan_block)}')
print(f'First 50: {repr(orphan_block[:50])}')

# Actually let me find the exact text of the orphan
# Find end of the line
eol1 = c.find(chr(10), orphan_idx)
line1 = c[orphan_idx:eol1]
eol2 = c.find(chr(10), eol1+1)
line2 = c[eol1+1:eol2]

print(f'Line 1: {repr(line1)}')
print(f'Line 2: {repr(line2)}')

# Remove these 2 lines
old = line1 + '\n' + line2 + '\n'
c = c.replace(old, '')

# Now insert proper routing in the MAIN routing chain
# Find the last elif before Draw Mode in the main chain
c_after_func = c[func_idx:]
main_draw = c_after_func.find('\n    elif st.session_state["studio_active_mode"] == "Draw Mode"')
print(f'\nMain Draw Mode routing (after func): {main_draw}')

# Show previous line
prev_nl = c_after_func.rfind(chr(10), 0, main_draw)
prev_line = c_after_func[prev_nl:main_draw]
print(f'Previous line: {repr(prev_line)}')

# Insert Production Engine route before Draw Mode
insert_point = func_idx + main_draw
route = '\n    elif st.session_state["studio_active_mode"] == "Production Engine":\n        run_production_engine_mode()'

c = c[:insert_point] + route + c[insert_point:]

# Write
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)

# Compile check
try:
    compile(c, 'app.py', 'exec')
    print('\nSUCCESS: app.py compiles OK!')
except Exception as e:
    print(f'\nERROR: {e}')
    
    # Show the error area
    err_line = int(str(e).split('line ')[1].split(',')[0]) if 'line ' in str(e) else 0
    if err_line > 0:
        lines = c.split(chr(10))
        print(f'\nAround line {err_line}:')
        for i in range(max(0, err_line-3), min(len(lines), err_line+3)):
            print(f'  {i}: {repr(lines[i][:120])}')
