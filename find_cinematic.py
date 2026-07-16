c = open('app.py','r',encoding='utf-8').read()

# Find run_cinematic_engine to see its input forms
func_start = c.find('def run_cinematic_engine(')
if func_start >= 0:
    # Print first 3000 chars
    print(c[func_start:func_start+3000])
