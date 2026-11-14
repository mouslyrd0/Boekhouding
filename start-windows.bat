@echo off
setlocal
title Mijn Archief
rem Start Mijn Archief vanuit de broncode.
rem Eenmalig nodig: Python 3.10 of nieuwer van https://www.python.org
rem De eerste keer worden de onderdelen gedownload; daarna werkt alles offline.

cd /d "%~dp0"

rem Al eerder geinstalleerd? Dan direct starten.
if exist ".venv\Scripts\pythonw.exe" goto starten

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
    echo  3. Dubbelklik daarna opnieuw op start-windows.bat.
    echo.
    pause
    exit /b 1
)

echo.
echo  Eerste keer starten: Mijn Archief wordt klaargezet.
echo  Dit duurt een paar minuten en heeft eenmalig internet nodig.
echo.
%PY% -m venv .venv || goto fout
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto fout
echo.
echo  Klaar. Vanaf nu start Mijn Archief direct en werkt het zonder internet.

:starten
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:fout
echo.
echo  Het klaarzetten is mislukt. Controleer of er internet is (alleen nodig bij de eerste keer)
echo  en dubbelklik daarna opnieuw op start-windows.bat.
if exist ".venv" rmdir /s /q ".venv"
pause
exit /b 1
