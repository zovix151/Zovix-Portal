c = open('app.py','r',encoding='utf-8').read()
idx = c.find('def run_cinematic_engine()')
section = c[idx:idx+36000]

# Find the render trigger handling where actual rendering happens
# Look for the block that handles trigger_render after rerun
for kw in ['if st.session_state.get("trigger_render"):', 
           'if "trigger_render" in st.session_state',
           'st.session_state["trigger_render"]']:
    p = 0
    while True:
        p = section.find(kw, p)
        if p < 0:
            break
        print(f'Found: "{kw}" at +{p}')
        print(section[p:p+2000])
        print("="*50)
        p += 1
