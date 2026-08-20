# Temp fix script - fix indentation on the voice type markdown line
import io

path = "app.py"
with io.open(path, "r", encoding="utf-8", newline="") as f:
    content = f.read()

old = "                        st.markdown('<p class=\"face-label\">🎭 Voice Type (Choose Manually)</p>', unsafe_allow_html=True)"
new = "            st.markdown('<p class=\"face-label\">🎭 Voice Type (Choose Manually)</p>', unsafe_allow_html=True)"

count = content.count(old)
print("occurrences of bad-indent markdown line:", count)
if count >= 1:
    content = content.replace(old, new, 1)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print("REPLACED OK")
else:
    print("NO MATCH FOUND")
