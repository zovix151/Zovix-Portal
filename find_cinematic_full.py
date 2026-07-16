c = open('app.py','r',encoding='utf-8').read()

# Find the full cinematic engine UI
idx = c.find('def run_cinematic_engine():')
if idx >= 0:
    next_def = c.find('\ndef ', idx + 30)
    if next_def < 0:
        next_def = len(c)
    content = c[idx:next_def]
    print(f'Total cinematic engine: {len(content)} chars')
    # Show the first part with all the input forms
    print(content[:6000])
    print('\n... (truncated) ...\n')
    print(content[-2000:])
