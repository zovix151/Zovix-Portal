c = open('app.py','r',encoding='utf-8').read()

# Find the get_premium_theme_css function
idx = c.find('def get_premium_theme_css()')
if idx >= 0:
    # Find the closing of the function
    next_def = c.find('\ndef ', idx + 30)
    if next_def < 0:
        next_def = len(c)
    content = c[idx:next_def]
    print(f'CSS Function: {len(content)} chars')
    print(content[:6000])
