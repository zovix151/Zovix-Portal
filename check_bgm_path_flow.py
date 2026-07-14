c = open('app.py','r',encoding='utf-8').read()
idx = c.find('def run_cinematic_engine()')
section = c[idx:idx+36000]

# Find where BGM path is resolved for Cinematic Engine
# Look for 'get_music_path' usage in the render block
p = section.find('get_music_path')
if p >= 0:
    print(f'get_music_path at +{p}')
    print(section[p-50:p+200])
    print('---')

# Find effective_bgm_path resolution
p = section.find('effective_bgm_path')
if p >= 0:
    print(f'\neffective_bgm_path at +{p}')
    print(section[p-100:p+300])
    print('---')

# Check what happens when BGM is uploaded
p = section.find('uploaded_bgm')
if p >= 0:
    # Find all occurrences in cinematic
    while True:
        p2 = section.find('uploaded_bgm', p)
        if p2 < 0:
            break
        print(f'uploaded_bgm at +{p2}: {section[p2:p2+150]}')
        p = p2 + 1
