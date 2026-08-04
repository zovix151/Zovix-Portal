"""
FINAL FIX: Replace empty function with full content + fix routing
"""
import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Extract the full function body from patch file
with open('patch_app_production.py', 'r', encoding='utf-8') as f:
    patch = f.read()

func_start = patch.find('def run_production_engine_mode()')
# Find where the function ends (before the ORIGINAL elif routing that was in the patch)
func_code = patch[func_start:]
# Find the marker that indicated end of function in the patch
route_marker = func_code.find('\n    elif st.session_state["studio_active_mode"] == "Draw Mode":')
if route_marker > 0:
    full_func = func_code[:route_marker]
else:
    # Fallback - find 3 newlines in a row
    triple_nl = func_code.find('\n\n\n')
    if triple_nl > 0:
        full_func = func_code[:triple_nl]
    else:
        full_func = func_code

print('Full function length:', len(full_func))

# 2. Remove the EMPTY function from app.py
empty_func_start = c.find('def run_production_engine_mode()')
# Find the end of the empty function (3 lines: def, docstring, blank)
after_empty = empty_func_start + len('def run_production_engine_mode():\n    ') 
# Next def or the orphan elif
rest_after = c[after_empty:]
next_def = rest_after.find('\ndef ')
next_elif = rest_after.find('\n    elif')
next_marker = min([i for i in [next_def, next_elif] if i > 0])

# But we need to find the exact end. Let's look for the "elif Production Engine" which is AFTER the empty function
pe_elif = rest_after.find('elif st.session_state["studio_active_mode"] == "Production Engine"')
if pe_elif > 0:
    empty_func_end = after_empty + pe_elif
else:
    # Just remove up to next def
    empty_func_end = after_empty + next_marker if next_marker > 0 else after_empty + 100

print(f'Empty function from {empty_func_start} to {empty_func_end}')

# Remove empty function
c = c[:empty_func_start] + c[empty_func_end:]

# 3. Insert the FULL function before the routing chain
# Find the first routing elif (Creative Workshop)
first_route = c.find('elif st.session_state["studio_active_mode"] == "Creative Workshop Mode"')
if first_route < 0:
    first_route = c.find('if st.session_state["studio_active_mode"] ==')

print(f'First route at: {first_route}')

# Insert FULL function before first routing
c = c[:first_route] + '\n\n' + full_func + '\n\n' + c[first_route:]

# 4. Insert Production Engine route into the routing chain (before Draw Mode)
draw_route = c.find('\n    elif st.session_state["studio_active_mode"] == "Draw Mode"')
pe_routing = '\n    elif st.session_state["studio_active_mode"] == "Production Engine":\n        run_production_engine_mode()'
c = c[:draw_route] + pe_routing + c[draw_route:]

# Write
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)

# Verify
try:
    compile(c, 'app.py', 'exec')
    print('\nSUCCESS: app.py compiles OK!')
except Exception as e:
    print('\nERROR:', e)
    # Show error context
    err_str = str(e)
    if 'line' in err_str:
        import re as _re2
        m = _re2.search(r'line (\d+)', err_str)
        if m:
            ln = int(m.group(1))
            lines = c.split('\n')
            print(f'Lines {ln-3} to {ln+2}:')
            for i in range(max(0,ln-4), min(len(lines), ln+3)):
                print(f'  {i}: [{len(lines[i])-len(lines[i].lstrip())}sp] {repr(lines[i][:100])}')
