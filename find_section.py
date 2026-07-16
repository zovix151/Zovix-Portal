c = open('app.py','r',encoding='utf-8').read()
# Find where the scheduler elif ends and the mode buttons section fully begins
# The mode buttons will be rendered for ANY tab that isn't the specific ones, so it's after all elifs
# Let's find the exact section that has the complete UI

# After scheduler block, look for the 'st.markdown' that starts the mode selection area
idx = c.find('st.markdown("<div class=\\'compact-label\\' style=\\'margin-bottom: 8px;\\'>Active Studio Workspace Mode</div>")')
if idx >= 0:
    print('Found mode header at:', idx)
    # Go backwards to find what section this is in
    before = c[max(0,idx-500):idx]
    print('Before (500 chars):')
    print(before)
    
# Also find the 'else' that starts the default rendering (scheduler block)
# After scheduler elif ends, there's likely an else: or it just falls through
print('\n\n=== Look for section structure ===')
idx2 = c.find('elif st.session_state["sidebar_tab"] == "📅 ADVANCED AI CONTENT SCHEDULER":')
rest = c[idx2:]
# Find closing of this elif - look for the next time we're back to studio page indentation
# The mode buttons are not inside any elif - they're in the default path
# Let's find what comes right after the scheduler div closes
# Look for the pattern that shows we exited the scheduler elif
lines = rest.split('\n')
for i, line in enumerate(lines[:100]):
    stripped = line.strip()
    # Look for lines that are not indented (start of a new block at top level)
    if stripped.startswith('st.markdown') or stripped.startswith('st.button') or stripped.startswith('elif'):
        print(f'Line {i}: [{len(line)-len(line.lstrip())} spaces] {stripped[:100]}')
