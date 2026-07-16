c = open('app.py','r',encoding='utf-8').read()

# Find the mode header using raw string
idx = c.find("Active Studio Workspace Mode")
if idx >= 0:
    print('Found mode header at:', idx)
    before = c[max(0,idx-400):idx]
    print('Before (400 chars):')
    print(before)

# Find section structure
print('\n\n=== Look for section structure ===')
idx2 = c.find('elif st.session_state["sidebar_tab"] == "')
rest = c[idx2:]
lines = rest.split('\n')
for i, line in enumerate(lines[:100]):
    stripped = line.strip()
    if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
        indent = len(line) - len(line.lstrip())
        if indent <= 4:
            print(f'Line {i} (indent={indent}): {stripped[:120]}')
