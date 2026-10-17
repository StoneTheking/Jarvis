@echo off
cd /d "%~dp0"
echo Installation de Jarvis...
python -m venv .venv || (echo Python 3.11+ est requis : https://www.python.org/downloads/ & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Installation terminee. Ouvre le fichier .env et colle ta cle API, puis lance lancer_jarvis.bat
pause
