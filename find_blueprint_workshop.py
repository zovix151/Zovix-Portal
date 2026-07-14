c = open('app.py','r',encoding='utf-8').read()

# Find deduct_credits calls to understand the pattern
idx = 0
while True:
    idx = c.find('deduct_credits', idx)
    if idx < 0:
        break
    print(f'=== deduct_credits at {idx} ===')
    print(c[idx-80:idx+250])
    idx += 1

# Find workshop image generation and convert to video section
idx_ws = c.find('Creative Workshop')
# Find the area where workshop generates images and has convert to video option
print('\n=== Workshop section ===')
idx_ws_section = c.find('def show_workshop_mode')
if idx_ws_section >= 0:
    end = c.find('\ndef ', idx_ws_section + 5)
    if end > 0:
        ws_code = c[idx_ws_section:end]
        # Find "convert" or "video" related code
        for kw in ['convert', 'video', 'token', 'credit', 'deduct']:
            pos = 0
            while True:
                pos = ws_code.find(kw, pos)
                if pos < 0:
                    break
                print(f'  {kw} at ws+{pos}: {ws_code[pos-30:pos+80]}')
                pos += 1
    else:
        print('  Could not find end of workshop function')

# Find Blueprints section
print('\n=== Blueprints section ===')
idx_bp = c.find('def show_blueprints_mode')
if idx_bp >= 0:
    end = c.find('\ndef ', idx_bp + 5)
    if end > 0:
        bp_code = c[idx_bp:end]
        for kw in ['save_render', 'token', 'credit', 'deduct', 'save']:
            pos = 0
            while True:
                pos = bp_code.find(kw, pos)
                if pos < 0:
                    break
                print(f'  {kw} at bp+{pos}: {bp_code[pos-30:pos+100]}')
                pos += 1
    else:
        print('  Could not find end of blueprints function')
