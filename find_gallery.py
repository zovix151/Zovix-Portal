c = open('app.py','r',encoding='utf-8').read()

# Find the get_mode_portfolio rendering section (after the function definition)
# Look for where the gallery is actually rendered
idx = c.find('def get_mode_portfolio')
print('get_mode_portfolio found at:', idx)
# Find its closing and the actual call/rendering
if idx >= 0:
    # Find the next def after it
    next_def = c.find('\ndef ', idx + len('def get_mode_portfolio'))
    if next_def > 0:
        print(c[idx:next_def])
    else:
        print(c[idx:idx+8000])
