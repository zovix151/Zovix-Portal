c = open('app.py','r',encoding='utf-8').read()
# Find what's between the scheduler elif and the studio_active_mode section
# Look for: after scheduler ends, before "if st.session_state['studio_active_mode']"
scheduler_start = c.find('elif st.session_state["sidebar_tab"] == "📅 ADVANCED AI CONTENT SCHEDULER":')
mode_start = c.find('if st.session_state["studio_active_mode"]')
# The scheduler block might end at the else/default section
# Let's look at the section between them
mid = c[scheduler_start:mode_start]
# Find the last elif/else before mode_start
lines = mid.split('\n')
last_section = '\n'.join(lines[-200:])  # last 200 lines
print('=== Last 200 lines before studio_active_mode ===')
print(last_section[:5000])
