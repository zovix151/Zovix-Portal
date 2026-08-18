import os

base = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base, 'app.py'), 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

lines = content.split('\n')
results = []
results.append(f"Total lines: {len(lines)}")
results.append("")

# Search for key auth-related keywords
keywords = ['landing_auth', 'google', 'facebook', 'login_btn', 'login_modal', 'auth_modal',
            'logged_in', 'logged_user', 'show_login', '2fa', 'oauth', 'sign_in', 'signin',
            'social_login', 'current_page == "landing"', 'current_page == "studio"', 
            'is_logged_in', 'auth_redirect_mode']

for i, line in enumerate(lines):
    lower = line.lower()
    for kw in keywords:
        if kw in lower:
            results.append(f"L{i+1}: {line.rstrip()[:300]}")
            break

# Write results to output
out_path = os.path.join(base, 'auth_search_results.txt')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print(f"Done. Found {len(results)-2} matching lines. Results written to auth_search_results.txt")