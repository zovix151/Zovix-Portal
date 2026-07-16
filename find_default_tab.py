c = open('app.py','r',encoding='utf-8').read()
# Find what comes after the scheduler block 
idx = c.find('elif st.session_state["sidebar_tab"] == "📅 ADVANCED AI CONTENT SCHEDULER":')
# skip past the scheduler block - look for end of file or next condition
rest = c[idx+50:]
# find the first condition that's NOT related to scheduler
pos = 0
while True:
    # Look for patterns like: if/elif at same indent level (no indent or 4 spaces)
    patterns = ['\n    if ', '\n    elif ', '\nelse:']
    next_marker = len(rest)
    for p in patterns:
        pp = rest.find(p)
        if pp >= 0 and pp < next_marker:
            next_marker = pp
    if next_marker >= len(rest):
        break
    snippet = rest[next_marker:next_marker+200]
    if 'scheduler' not in snippet.lower() and 'sch_' not in snippet:
        print(f'Found at {next_marker} from scheduler:')
        print(snippet)
        # Print the next 3000 chars
        print('---CONTENT---')
        print(rest[next_marker:next_marker+3000])
        break
    pos = next_marker + 1
    rest = rest[pos:]
