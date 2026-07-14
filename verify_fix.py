c = open('engine.py', 'r', encoding='utf-8').read()

# Check old hardcoded logic
old_pattern = '"21m00Tcm4TlvDq8ikWAM" if "Drew" in voice_profile'
if old_pattern in c:
    print('❌ OLD hardcoded logic STILL EXISTS! Fix failed!')
else:
    print('✅ OLD hardcoded logic REMOVED successfully')

# Check new resolver
new = '_resolve_cinematic_voice_id(voice_profile)'
if new in c:
    idx = c.find(new)
    print(f'✅ New resolver call in place at pos {idx}')
else:
    print('❌ New resolver NOT found!')

# Check BGM
bgm = c.count('bgm_path')
print(f'✅ BGM references: {bgm}')

# Check helper dict
for name in ['Adam (Premium Male)', 'Rachel (Premium Female)', 'Drew (Premium Male)']:
    if name in c:
        print(f'✅ Voice mapping found: {name}')
    else:
        print(f'❌ Missing: {name}')

try:
    compile(c, 'engine.py', 'exec')
    print('✅ FINAL SYNTAX CHECK PASSED!')
except SyntaxError as e:
    print(f'❌ SYNTAX ERROR: {e}')

