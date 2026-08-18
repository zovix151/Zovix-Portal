import sys

with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the problematic line and the function definition
target = None
func_start = None
for i, line in enumerate(lines):
    if 'st.session_state["user_prompt"] = user_input' in line:
        target = i
    if line.strip().startswith("def run_cinematic_engine"):
        func_start = i

print(f"Function starts at line {func_start + 1}")
print(f"Problematic line at {target + 1}")

# Print surrounding context
if target is not None:
    start = max(0, target - 30)
    end = min(len(lines), target + 20)
    print(f"\n=== Context lines {start + 1} to {end} ===")
    for i in range(start, end):
        print(f"{i + 1}| {lines[i]}", end="")