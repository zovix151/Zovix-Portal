c = open('app.py','r',encoding='utf-8').read()
print('1. current_page refs:', c.count('current_page'))
print('2. WorldClassLandingPage:', 'WorldClassLandingPage' in c)
print('3. landing_page.py import:', 'landing_page' in c)

idx = c.find('"current_page"')
if idx >= 0:
    print(f'\nFirst current_page at {idx}: {c[max(0,idx-100):idx+100]}')

idx2 = c.find('if st.session_state')
if idx2 >= 0:
    context = c[idx2:idx2+500]
    print(f'\nFirst if st.session_state: {context}')
