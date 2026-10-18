@echo off
setlocal
rem Ce fichier se copie ailleurs avant de travailler, car il va etre remplace pendant la mise a jour.
if not "%~1"=="--copie" (
    copy /y "%~f0" "%TEMP%\jarvis_mise_a_jour.bat" >nul
    "%TEMP%\jarvis_mise_a_jour.bat" --copie "%~dp0"
    exit /b
)
cd /d "%~2"
echo === Mise a jour de Jarvis ===
echo Dossier : %CD%
echo.

set "URL=https://github.com/StoneTheking/Jarvis/archive/refs/heads/claude/busy-hopper-wabowu.zip"
set "TMPD=%TEMP%\jarvis_maj"
if exist "%TMPD%" rmdir /s /q "%TMPD%"
mkdir "%TMPD%"

echo Telechargement de la derniere version...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest -UseBasicParsing '%URL%' -OutFile '%TMPD%\jarvis.zip'; Expand-Archive -Force '%TMPD%\jarvis.zip' '%TMPD%'"
if errorlevel 1 (
    echo [ERREUR] Telechargement impossible. Verifie ta connexion internet.
    pause
    exit /b 1
)
set "SRC="
for /d %%d in ("%TMPD%\Jarvis-*") do set "SRC=%%d"
if not defined SRC (
    echo [ERREUR] Archive inattendue.
    pause
    exit /b 1
)

if exist config.toml (
    copy /y config.toml config.ancien.toml >nul
    echo Ton ancienne configuration est sauvegardee dans config.ancien.toml
)

echo Copie des nouveaux fichiers...
robocopy "%SRC%" "%CD%" /E /XD .venv .git /XF .env /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo [ERREUR] La copie des fichiers a echoue. Ferme Jarvis s'il est ouvert, puis relance.
    pause
    exit /b 1
)
rmdir /s /q "%TMPD%"

if exist .venv\Scripts\python.exe (
    echo Verification des modules...
    .venv\Scripts\python.exe -m pip install -q -r requirements.txt
    .venv\Scripts\python.exe -m pip install -q faster-whisper >nul 2>nul
)

echo.
echo === Mise a jour terminee ! ===
echo Si tu avais ajoute des contacts ou des applis dans l'ancienne config,
echo recopie-les depuis config.ancien.toml dans config.toml.
echo Tu peux maintenant lancer lancer_jarvis.bat
pause
