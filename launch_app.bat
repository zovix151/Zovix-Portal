@echo off
cd /d "c:\Zovix-Clean"
echo Checking syntax...
python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read()); print('SYNTAX-OK')"
if %ERRORLEVEL% NEQ 0 (
    echo Syntax error found! Check app.py.
    pause
    exit /b 1
)
echo Syntax clean! Launching app...
streamlit run app.py --server.port 8501
pause