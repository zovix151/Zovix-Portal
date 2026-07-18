c = open('app.py','r',encoding='utf-8').read()

# Find the landing page rendering in app.py
idx = c.find('if st.session_state["current_page"] == "landing":')
if idx >= 0:
    # Print the whole landing block
    end = c.find('elif st.session_state["current_page"] == "studio":', idx)
    print(c[idx:end])
