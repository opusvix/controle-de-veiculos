@echo off
cd /d "%~dp0"
set "PYW=%LocalAppData%\Programs\Python\Python312\pythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" "%~dp0main.py"
) else (
    start "" pythonw "%~dp0main.py"
)
