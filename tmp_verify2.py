# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
with open("deepinfra_engine.py", encoding='utf-8') as f:
    lines = f.readlines()

print("=== generate_face_video method (165 -> 250) ===")
for i in range(164, 250):
    print(f"{i+1}: {lines[i].rstrip()}")
