c = open('app.py','r',encoding='utf-8').read()
idx = c.find('elif st.session_state["current_page"] == "studio":')
if idx >= 0:
    end = c.find('\nelif', idx+5)
    if end < 0:
        end = c.find('\nif st.session_state', idx+1)
    if end < 0:
        end = idx + 10000
    print(f'Studio page block ({end-idx} chars):')
    print(c[idx:min(len(c), end)])
else:
    print('Not found, trying alternate search...')
    # find all the elif blocks
    idx = c.find('elif st.session_state', 519000)
    while idx >= 0:
        end_br = c.find('\n', idx)
        print(f'  Found at {idx}: {c[idx:end_br]}')
        idx = c.find('elif st.session_state', end_br)
