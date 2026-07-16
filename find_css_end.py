c = open('app.py','r',encoding='utf-8').read()

# Find the get_premium_theme_css function full content
idx = c.find('def get_premium_theme_css()')
if idx >= 0:
    next_def = c.find('\ndef ', idx + 30)
    if next_def < 0:
        next_def = len(c)
    content = c[idx:next_def]
    
    # Find what comes after the CSS (the new CSS additions)
    # I want to add the Dark-Neon render page CSS
    print(f'Full CSS function: {len(content)} chars')
    
    # Show the end of the CSS
    print('\n=== Last 500 chars ===')
    print(content[-500:])
