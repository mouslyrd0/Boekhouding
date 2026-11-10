@echo off
rem Start Mijn Archief vanuit de broncode (alternatief voor het installatieprogramma).
rem Eenmalig nodig: Python 3.10 of nieuwer (https://www.python.org, vink "Add to PATH" aan).
rem De eerste keer worden de onderdelen gedownload; daarna werkt alles offline.

cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python is niet gevonden. Installeer Python 3 via https://www.python.org en vink "Add python.exe to PATH" aan.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\pythonw.exe" (
    echo Eerste keer starten: onderdelen installeren...
    python -m venv .venv || goto fout
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto fout
)
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:fout
echo Installeren is mislukt. Controleer de internetverbinding (alleen nodig bij de eerste keer) en probeer opnieuw.
pause
exit /b 1
