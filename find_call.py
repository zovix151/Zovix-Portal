c = open('app.py','r',encoding='utf-8').read()
# Let's find what comes after the entire get_mode_portfolio definition
idx = c.find('def get_mode_portfolio')
if idx >= 0:
    # Find the end by looking for the next content at 4-space indent level
    # that calls the function
    # Search for "valid_items, gallery_title, no_items_msg, display_type = get_mode_portfolio"
    call_idx = c.find('valid_items, gallery_title, no_items_msg, display_type = get_mode_portfolio')
    if call_idx > 0:
        print(f'Function call at {call_idx}')
        print(c[call_idx:call_idx+3000])
