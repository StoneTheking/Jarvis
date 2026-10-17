@echo off
cd /d "%~dp0"
echo Installation de Jarvis...
python -m venv .venv || (echo Python 3.11+ est requis : https://www.python.org/downloads/ & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Installation terminee. Connecte ton abonnement Claude (voir README, etape 4), puis lance lancer_jarvis.bat
pause
