# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
def w(a,b,title):
    with open("app.py", encoding='utf-8') as f:
        lines=f.readlines()
    print(f"===== {title} lines {a}-{b} =====")
    for i in range(a-1,b):
        print(f"{i+1}: {lines[i].rstrip()}")

w(975, 1000, "AI Agent session config")
w(15085, 15105, "Call site 1 context")
w(15755, 15775, "Call site 2 context")
w(1165, 1180, "AI Agent nav index")
w(1620, 1700, "ai_agent_config table & related")
