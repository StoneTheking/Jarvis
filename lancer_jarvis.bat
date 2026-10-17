@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist .venv\Scripts\python.exe (
    echo Jarvis n'est pas encore installe : lancement de l'installation...
    call installer.bat
    if not exist .venv\Scripts\python.exe exit /b 1
)
.venv\Scripts\python.exe -m jarvis %*
pause
