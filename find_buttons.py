c = open('app.py','r',encoding='utf-8').read()
# Find the mode buttons section to see complete UI
idx = c.find('mode_buttons = ["👤 Face Video", "🎬 Cinematic", "🎨 Creative"')
if idx >= 0:
    # Print from there until the "if st.session_state['studio_active_mode']" section
    mode_start = c.find('if st.session_state["studio_active_mode"]', idx)
    print('Mode buttons at:', idx)
    print('Studio active mode at:', mode_start)
    print('=== Content between ===')
    print(c[idx:mode_start])
