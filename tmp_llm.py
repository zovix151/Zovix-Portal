# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
with open("app.py", encoding='utf-8') as f:
    lines=f.readlines()
keys = ['DEEPSEEK_API','deepseek_api','deepseek','api.deepseek','DEEPSEEK_','gemini','GEMINI_API','generativelanguage','chat/completions','anthropic','together.ai','openai']
for i,line in enumerate(lines):
    low=line.lower()
    for k in keys:
        if k in low:
            print(f"{i+1}: {line.rstrip()}")
            break
