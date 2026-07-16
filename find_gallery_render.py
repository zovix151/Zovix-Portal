c = open('app.py','r',encoding='utf-8').read()

# After get_mode_portfolio function, there's the call to render the gallery
# Find what comes after the function definition ends
idx = c.find('def get_mode_portfolio')
if idx >= 0:
    func_end = c.find('gallery_title', idx + 10000)
    if func_end > 0:
        # Find the end of this function - next def or end of file
        # Look for line starting with 'if' or 'st.markdown' or 'with' at indentation level 4
        # Actually the function returns, so look for 'return' then after that
        ret_idx = c.find('\n        return valid_items, gallery_title, no_items_msg, display_type\n', func_end)
        if ret_idx > 0:
            print(f'Return at {ret_idx}')
            # After this, the function is closed, then the next block renders the gallery
            after_ret = ret_idx + len('\n        return valid_items, gallery_title, no_items_msg, display_type\n')
            # The next line should close the function with proper indent
            print('After return (500 chars):')
            print(c[after_ret:after_ret+500])
