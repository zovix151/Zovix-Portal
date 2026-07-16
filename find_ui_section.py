c = open('app.py','r',encoding='utf-8').read()

# Get the full studio render section - from mode header down to the end of file
# This is the default render page (Mass Factory tab)
start = c.find('Active Studio Workspace Mode</div>", unsafe_allow_html=True)')
if start >= 0:
    start -= 100  # include the st.markdown call
    # Find the actual start
    real_start = c.rfind('\n', 0, start) + 1
    print(f'Section starts at {real_start}')
    # Go to end of file
    print(f'Section to EOF: {len(c) - real_start} chars')
    # Print the first 4000 chars
    print(c[real_start:real_start+4000])
