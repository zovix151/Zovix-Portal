c = open('app.py','r',encoding='utf-8').read()
idx = c.find('def run_cinematic_engine()')
section = c[idx:idx+36000]

# Find the render pipeline section AFTER trigger_render handling
p = section.find('trigger_render')
p = section.find('if st.session_state["trigger_render"]:', p)
print('=== Full render pipeline ===')
print(section[p:p+5000])
