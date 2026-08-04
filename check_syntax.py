import ast, pathlib
src = pathlib.Path(r'c:\Zovix-Clean\app.py').read_text(encoding='utf-8')
try:
    ast.parse(src)
    print('syntax-ok')
except SyntaxError as e:
    print('line', e.lineno, 'offset', e.offset, 'msg', e.msg)
    if e.lineno:
        lines = src.splitlines()
        if 1 <= e.lineno <= len(lines):
            print(lines[e.lineno-1])
