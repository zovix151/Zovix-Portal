# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
with open("app.py", encoding='utf-8') as f:
    lines=f.readlines()
keys = ['def generate_ad','def generate_instagram','def generate_image','def call_deepseek','def deepseek','def generate_with_gemini','def gemini','def generate_marketing','def generate_ad_copy','def _generate_text','def generate_prompt_from']
for i,line in enumerate(lines):
    low=line.lower()
    if low.startswith('def ') and ('deepseek' in low or 'gemini' in low or 'generate_ads' in low or 'generate_image' in low or 'call_llm' in low or 'generate_text' in low or 'generate_ad' in low or 'image_' in low):
        print(f"{i+1}: {line.rstrip()}")
