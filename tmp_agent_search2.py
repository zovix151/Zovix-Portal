# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
with open("app.py", encoding='utf-8') as f:
    lines=f.readlines()
keys = ['agent_generated_ad','agent_instagram','agent_business_name','agent_products','agent_schedule','ai_agent_mode','def render_ai_sales_ui','def generate_.*ad','def render_ai_agent','instagram_caption','ai_agent_config']
for i,line in enumerate(lines):
    low=line.lower()
    for k in keys:
        if k.lower() in low:
            print(f"{i+1}: {line.rstrip()}")
            break
