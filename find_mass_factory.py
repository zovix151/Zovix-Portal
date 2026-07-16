c = open('app.py','r',encoding='utf-8').read()
# Find the Mass Factory block
idx = c.find('sidebar_tab == "🚀 Zovix Mass Factory"')
if idx < 0:
    idx = c.find('Zovix Mass Factory', 520000)
print('Found at:', idx)
if idx >= 0:
    # print 3000 chars after this
    print(c[idx:idx+3000])
