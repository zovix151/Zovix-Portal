# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
with open("app.py", encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    low = line.lower()
    if 'ai agent' in low or 'ai_agent' in low or 'def run_ai_agent' in low or 'agent_mode' in low:
        print(f"{i+1}: {line.rstrip()}")
