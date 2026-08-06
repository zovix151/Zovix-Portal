@echo off
cd /d c:\Zovix-Clean
python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('SYNTAX-OK')" 2>check_err.txt
type check_err.txt