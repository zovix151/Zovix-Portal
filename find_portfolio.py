c = open('app.py','r',encoding='utf-8').read()

# Find the 'hr' separator and what comes after (the portfolio section)
hr_idx = c.find('st.markdown("<hr style=\\'border-color:', 536600)
if hr_idx >= 0:
    print(f'HR separator at {hr_idx}')
    print(c[hr_idx:hr_idx+5000])
