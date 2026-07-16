c = open('app.py','r',encoding='utf-8').read()
idx = 0
count = 0
seen = set()
while True:
    idx = c.find('sidebar_tab ==', idx+1)
    if idx < 0: break
    line_start = c.rfind('\n', 0, idx) + 1
    line_end = c.find('\n', idx)
    line = c[line_start:line_end].strip()
    if line not in seen:
        print(f'Found at {idx}: {line}')
        seen.add(line)
    count += 1
