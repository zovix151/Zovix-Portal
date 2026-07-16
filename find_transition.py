c = open('app.py','r',encoding='utf-8').read()
# After the scheduler block closes (after the last div/unsafe_allow_html statement),
# the next non-indented code is the mode buttons section
# Let's find: scheduler block opening, then trace to find where it ends

sch_start = c.find('elif st.session_state["sidebar_tab"] == "📅 ADVANCED AI CONTENT SCHEDULER":')
# Go to the st.markdown("<div class='compact-label'... which starts the mode section
mode_header = c.find("Active Studio Workspace Mode", sch_start)
print(f'Scheduler at {sch_start}, mode header at {mode_header}')
print(f'Gap: {mode_header - sch_start} chars')

# Let's see the exact transition
print('\n=== 100 chars before mode header ===')
print(repr(c[mode_header-100:mode_header]))
print('\n=== Mode header itself ===')
print(repr(c[mode_header:mode_header+100]))
