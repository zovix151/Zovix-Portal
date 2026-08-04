import re
with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

orphan_block = '''elif st.session_state["studio_active_mode"] == "Production Engine":
        run_production_engine_mode()'''

orphan_idx = c.find('elif st.session_state["studio_active_mode"] == "Production Engine"')
draw_idx = c.find('\n    elif st.session_state["studio_active_mode"] == "Draw Mode":')

# Remove orphan elif
c = c[:orphan_idx] + c[orphan_idx + len(orphan_block):]

# Recalculate draw_idx after removal
new_draw_idx = c.find('\n    elif st.session_state["studio_active_mode"] == "Draw Mode":')
# Insert proper routing before Draw Mode
new_route = '\n    elif st.session_state["studio_active_mode"] == "Production Engine":\n        run_production_engine_mode()'
c = c[:new_draw_idx] + new_route + c[new_draw_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)

print('Fix applied!')

# Verify
try:
    compile(c, 'app.py', 'exec')
    print('app.py compiles OK!')
except Exception as e:
    print('ERROR: ' + str(e))

