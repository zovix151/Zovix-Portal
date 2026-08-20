import ast
import sys

# 1. syntax check
try:
    with open("app.py", encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)
    print("SYNTAX OK")
except Exception as e:
    print("SYNTAX ERROR:", e)
    sys.exit(1)

# 2. Check validate_and_deduct_tokens call signature consistency
# Find all call sites that unpack 3 values
import re
for m in re.finditer(r"(\w+),\s*(\w+),\s*(\w+)\s*=\s*validate_and_deduct_tokens\(", src):
    print("3-tuple unpack:", m.group(0))

# find single-ref calls where it's compared to True
for m in re.finditer(r"(\w+)\s*=\s*validate_and_deduct_tokens\([^)]*\)\s*\n\s*if\s+\1\s+is\s+not\s+True", src):
    print("boolean-compare (is not True) detected at pos", m.start())
