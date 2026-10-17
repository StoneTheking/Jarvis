@echo off
cd /d "%~dp0"
echo === Installation de Jarvis ===
echo.
where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python est introuvable. Installe-le depuis https://www.python.org/downloads/
    echo          en cochant bien "Add Python to PATH", puis relance ce fichier.
    pause
    exit /b 1
)
python -c "import sys; sys.exit(sys.version_info < (3, 11))"
if errorlevel 1 (
    echo [ERREUR] Jarvis a besoin de Python 3.11 ou plus recent.
    python --version
    pause
    exit /b 1
)
python --version
if not exist .venv\Scripts\python.exe (
    echo Creation de l'environnement Python...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement Python.
        pause
        exit /b 1
    )
)
echo Installation des modules (ca peut prendre quelques minutes)...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERREUR] L'installation des modules a echoue. Fais une capture des messages
    echo          ci-dessus et envoie-la pour qu'on corrige.
    pause
    exit /b 1
)
echo.
echo === Installation terminee ! ===
echo Si ce n'est pas deja fait, connecte ton abonnement Claude (README, etape 4),
echo puis lance lancer_jarvis.bat
pause
