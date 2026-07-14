# encoding: utf-8
import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Find and count all st.dialog occurrences
matches = list(re.finditer(r'with st\.dialog\(', c))
print(f"Found {len(matches)} st.dialog occurrences")

for i, m in enumerate(matches):
    pos = m.start()
    # Find the end of this dialog block - look for next st.markdown end or similar
    print(f"\n=== Dialog #{i+1} at pos {pos} ===")
    # Get a bigger context
    ctx = c[max(0,pos-100):pos+500]
    print(ctx[:600])
