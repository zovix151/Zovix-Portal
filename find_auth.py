import os

base = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base, 'app.py'), 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

lines = content.split('\n')
results = [f"Total lines: {len(lines)}"]

for i, line in enumerate(lines):
    lower = line.lower()
    for kw in ['landing_auth', 'google', 'facebook', 'logged_in', 'logged_user', 'login', 'oauth', 'auth_redirect']:
        if kw in lower:
            results.append(f"L{i+1}: {line.rstrip()[:200]}")
            break

with open(os.path.join(base, 'auth_results.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))