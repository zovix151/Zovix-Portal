c = open('app.py','r',encoding='utf-8').read()

# Find the end of get_premium_theme_css and where we can add render_page_css
css_end = c.find("    </style>\n    \"\"\"")
if css_end >= 0:
    print(f'CSS return end at {css_end}')
    # Show the context around it
    print(c[css_end-300:css_end+100])
