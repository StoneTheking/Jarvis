@echo off
setlocal
cd /d "%~dp0"
echo === Installation de Jarvis ===
echo.

rem Choix de Python : on prefere une version compatible avec Whisper (3.11 a 3.14).
set "PY="
for %%v in (3.13 3.14 3.12 3.11) do (
    if not defined PY (
        py -%%v -c "" >nul 2>nul && set "PY=py -%%v"
    )
)
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERREUR] Python est introuvable. Installe-le depuis https://www.python.org/downloads/
    echo          en cochant bien "Add Python to PATH", puis relance ce fichier.
    pause
    exit /b 1
)
%PY% -c "import sys; sys.exit(sys.version_info < (3, 11))"
if errorlevel 1 (
    echo [ERREUR] Jarvis a besoin de Python 3.11 ou plus recent.
    %PY% --version
    pause
    exit /b 1
)
for /f %%i in ('%PY% -c "import sys; print(*sys.version_info[:2], sep=chr(46))"') do set "VERSION=%%i"
echo Python utilise : %VERSION%

rem Si l'environnement existant a ete cree avec une autre version de Python, on le recree.
if exist .venv\Scripts\python.exe (
    for /f %%i in ('.venv\Scripts\python.exe -c "import sys; print(*sys.version_info[:2], sep=chr(46))"') do set "VERSION_VENV=%%i"
)
if defined VERSION_VENV if not "%VERSION_VENV%"=="%VERSION%" (
    echo Ancien environnement Python %VERSION_VENV% : remplacement par Python %VERSION%...
    rmdir /s /q .venv
)
if not exist .venv\Scripts\python.exe (
    echo Creation de l'environnement Python...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer l'environnement Python.
        pause
        exit /b 1
    )
)

echo Installation des modules ^(ca peut prendre quelques minutes^)...
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
echo Installation de Whisper ^(reconnaissance vocale sur ton PC^)...
.venv\Scripts\python.exe -m pip install faster-whisper
if errorlevel 1 (
    echo.
    echo [INFO] Whisper n'est pas encore disponible pour Python %VERSION%.
    echo        Jarvis marchera quand meme, avec la reconnaissance vocale de Google.
    echo        Pour avoir Whisper ^(il comprend bien mieux^) : installe aussi Python 3.13
    echo        depuis https://www.python.org/downloads/ puis relance installer.bat,
    echo        il le choisira automatiquement.
)

echo.
echo === Installation terminee ! ===
echo Si ce n'est pas deja fait, connecte ton abonnement Claude ^(README, etape 4^),
echo puis lance lancer_jarvis.bat
pause
