c = open('app.py','r',encoding='utf-8').read()
idx = c.find('def run_cinematic_engine()')
section = c[idx:idx+36000]

# Continue from where the last snippet ended - data_snapshot creation
p = section.find('size_choi')
print(section[p:p+3000])
