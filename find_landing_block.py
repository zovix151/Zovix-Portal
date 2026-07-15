c = open('app.py','r',encoding='utf-8').read()
idx = c.find('if st.session_state["current_page"] == "landing":', 519800)
if idx >= 0:
    end = c.find('\nelif', idx)
    if end < 0:
        end = idx + 2000
    print(f'Landing block ({end-idx} chars):')
    print(c[idx:end])
else:
    print('Not found')
    # Try alternate patterns
    idx = c.find('current_page', 519800)
    if idx >= 0:
        print(f'Found at {idx}: {c[idx:idx+200]}')
