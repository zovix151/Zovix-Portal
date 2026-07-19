import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function
func_start = content.find('def generate_drawing_hybrid')
rest = content[func_start+100:]
matches = list(re.finditer(r'(?<=\n)(?:def |class |# ={3,})', rest, re.MULTILINE))
end = func_start + 100 + matches[0].start()
old_func = content[func_start:end]

# Find the exact last lines for matching
last_line = old_func.split('\n')[-2]  # Last line before blank
print(f"LAST LINE: {repr(last_line)}")

# Find unique portion to match
for line in old_func.split('\n'):
    if 'generate_enhanced_fallback_drawing' in line:
        print(f"MATCH LINE: {repr(line)}")

# Write old_func to file for reference
with open('old_func_check.txt', 'w', encoding='utf-8') as f:
    f.write(old_func)
print(f"Written {len(old_func)} chars to old_func_check.txt")
