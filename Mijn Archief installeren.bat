@echo off
setlocal
title Mijn Archief installeren
rem Zet Mijn Archief klaar en maakt een snelkoppeling "Mijn Archief" op het
rem bureaublad en in het Startmenu. Dit hoeft maar een keer.
rem Eenmalig nodig: Python 3.10 of nieuwer van https://www.python.org

cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" goto snelkoppeling

rem Python zoeken: eerst de 'py'-starter van python.org, dan 'python'.
set "PY="
where py >nul 2>nul && py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo.
    echo  Python is niet gevonden.
    echo.
    echo  1. Ga naar https://www.python.org/downloads/ en klik op "Download Python".
    echo  2. Vink onderaan "Add python.exe to PATH" aan en klik op "Install Now".
    echo  3. Dubbelklik daarna opnieuw op "Mijn Archief installeren".
    echo.
    pause
    exit /b 1
)

echo.
echo  Mijn Archief wordt geinstalleerd.
echo  Dit duurt een paar minuten en heeft eenmalig internet nodig.
echo.
%PY% -m venv .venv || goto fout
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto fout

:snelkoppeling
powershell -NoProfile -ExecutionPolicy Bypass -File "packaging\snelkoppelingen.ps1" -AppDir "%CD%"
if errorlevel 1 (
    echo.
    echo  Het programma is geinstalleerd, maar de snelkoppeling kon niet worden gemaakt.
    echo  Je kunt Mijn Archief starten door opnieuw op dit bestand te dubbelklikken.
    echo.
    pause
) else (
    echo.
    echo  Klaar. Je vindt "Mijn Archief" nu op je bureaublad en in het Startmenu.
    echo  Vanaf nu werkt het programma zonder internet.
    timeout /t 4 >nul
)
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:fout
echo.
echo  Het installeren is mislukt. Controleer of er internet is (alleen nodig bij de eerste keer)
echo  en dubbelklik daarna opnieuw op "Mijn Archief installeren".
if exist ".venv" rmdir /s /q ".venv"
pause
exit /b 1
