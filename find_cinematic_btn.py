c = open('app.py','r',encoding='utf-8').read()
idx = c.find('def run_cinematic_engine()')
section = c[idx:idx+36000]

# Find button or compilation trigger
for kw in ['st.button("Compile', 'st.button("Generate', 'st.button("Render', 'st.button("▶', 'st.button("🎬',
            'st.button("⚡', 'Compile Video', 'Generate Movie', 'Render Film']:
    p = section.find(kw)
    if p >= 0:
        print(f'Found: at +{p}')
        print(section[p:p+400])
        print('---')

# Find where bgm_volume is used before compilation
print("\n=== bgm_volume references in section ===")
p = 0
while True:
    p = section.find('bgm_volume', p)
    if p < 0:
        break
    print(f'  +{p}: {section[p:p+100]}')
    p += 1
