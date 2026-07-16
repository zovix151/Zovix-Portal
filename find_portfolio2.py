c = open('app.py','r',encoding='utf-8').read()
# Find the 'hr' separator and what comes after (the portfolio section)
hr_idx = c.find("border-color: rgba(255,255,255,0.08); margin: 30px 0;", 536600)
if hr_idx >= 0:
    # go back to the st.markdown call
    line_start = c.rfind('\n', 0, hr_idx) + 1
    print(f'HR separator line at {line_start}')
    print(c[line_start:line_start+5000])
