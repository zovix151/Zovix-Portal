c = open('app.py','r',encoding='utf-8').read()
# Find the scheduler block end and see what comes after
idx = c.find('elif st.session_state["sidebar_tab"] == "📅 ADVANCED AI CONTENT SCHEDULER":')
print('Scheduler block at:', idx)
if idx >= 0:
    # Find the next sidebar_tab check or the end of this elif block
    # After scheduler, there should be the default (mass factory) tab
    next_elif = c.find('\nelif', idx)
    next_if = c.find('\nif st.session_state', idx)
    next_default = c.find('\nelse:', idx)
    
    # Find the first occurrence of any of these after the scheduler block
    # Let's look for the next function definition or the very next conditional
    candidates = []
    for term in ['\nelif', '\nif ', '\nelse:', '\ndef ', '\n# ===']:
        pos = c.find(term, idx+50)
        if pos >= 0:
            candidates.append((pos, term))
    candidates.sort()
    print('Next significant markers after scheduler:')
    for pos, term in candidates[:5]:
        print(f'  {term} at {pos}: {c[pos:pos+80]}')
    
    # Print from scheduler start to next block
    end_pos = candidates[0][0] if candidates else idx+3000
    print('\n--- Scheduler to next block ---')
    print(c[idx:end_pos])
