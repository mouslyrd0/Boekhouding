@echo off
setlocal EnableExtensions
title Raspberry Pi instellen voor Mijn Archief
cd /d "%~dp0"
chcp 65001 >nul

echo.
echo  ==============================================================
echo   Raspberry Pi instellen voor Mijn Archief
echo  ==============================================================
echo.
echo  Dit zet vanaf deze pc een gedeelde map "MijnArchief" klaar op je
echo  Raspberry Pi. Alles gaat via je eigen thuisnetwerk.
echo.
echo  Nodig: de Pi staat aan, zit op hetzelfde netwerk en SSH staat aan.
echo.

where ssh >nul 2>nul
if errorlevel 1 (
    echo  SSH is niet gevonden op deze pc.
    echo  Ga naar Instellingen ^> Apps ^> Optionele onderdelen ^> Onderdeel toevoegen
    echo  en installeer "OpenSSH-client". Start dit bestand daarna opnieuw.
    echo.
    pause
    exit /b 1
)
if not exist "raspberry\installeer-op-raspberry.sh" (
    echo  Het bestand raspberry\installeer-op-raspberry.sh ontbreekt.
    echo  Pak de zip opnieuw volledig uit en probeer het nog eens.
    pause
    exit /b 1
)

set "PI=raspberrypi.local"
set /p "PI=  Naam of IP-adres van de Pi [raspberrypi.local]: "
set "GEBRUIKER="
set /p "GEBRUIKER=  Gebruikersnaam op de Pi (zoals ingesteld bij installatie): "
if not defined GEBRUIKER (
    echo  Je hebt geen gebruikersnaam ingevuld.
    pause
    exit /b 1
)
echo.
echo  Waar moet het archief op de Pi komen?
echo  Druk op Enter voor de standaardmap /srv/mijnarchief, of typ een eigen
echo  map, bijvoorbeeld /mnt/ssd/mijnarchief voor een vast gekoppelde USB-schijf.
set "MAP=/srv/mijnarchief"
set /p "MAP=  Map op de Pi [/srv/mijnarchief]: "

echo.
echo  --------------------------------------------------------------
echo   Stap 1 van 2: het installatiescript naar de Pi kopieren.
echo   Typ het wachtwoord van je Pi-gebruiker als daarom gevraagd wordt
echo   (je ziet tijdens het typen geen tekens, dat is normaal).
echo  --------------------------------------------------------------
scp -o StrictHostKeyChecking=accept-new "raspberry\installeer-op-raspberry.sh" "%GEBRUIKER%@%PI%:mijnarchief-installeer.sh"
if errorlevel 1 goto geenverbinding

echo.
echo  --------------------------------------------------------------
echo   Stap 2 van 2: installeren op de Pi.
echo   Je typt opnieuw het Pi-wachtwoord. Daarna kies je een wachtwoord
echo   voor de gedeelde map (twee keer typen).
echo  --------------------------------------------------------------
ssh -t -o StrictHostKeyChecking=accept-new "%GEBRUIKER%@%PI%" "sed -i 's/\r$//' ~/mijnarchief-installeer.sh && sudo bash ~/mijnarchief-installeer.sh '%MAP%'; status=$?; rm -f ~/mijnarchief-installeer.sh; exit $status"
if errorlevel 1 (
    echo.
    echo  De installatie op de Pi is niet gelukt. Lees de melding hierboven.
    echo  Je kunt dit bestand gerust opnieuw starten.
    echo.
    pause
    exit /b 1
)


echo.
echo  ==============================================================
echo   Klaar! Nu nog een keer inloggen op de gedeelde map.
echo  ==============================================================
echo.
echo  Er gaat zo een Verkenner-venster open naar:
echo.
echo      \\%PI%\MijnArchief
echo.
echo  Log in met gebruikersnaam %GEBRUIKER% en het wachtwoord voor de
echo  gedeelde map. Vink "Mijn referenties onthouden" aan.
echo.
echo  Daarna in Mijn Archief:
echo    Bestand ^> Archief verhuizen ^> typ \\%PI%\MijnArchief
echo.
pause
start "" explorer "\\%PI%\MijnArchief"
exit /b 0

:geenverbinding
echo.
echo  Er kon geen verbinding worden gemaakt met de Pi (%PI%).
echo  Controleer:
echo   - staat de Pi aan en zit hij op hetzelfde netwerk als deze pc?
echo   - staat SSH aan op de Pi? (Raspberry Pi Imager: "SSH inschakelen",
echo     of op de Pi zelf: sudo raspi-config ^> Interface Options ^> SSH)
echo   - kloppen de naam en de gebruikersnaam? Probeer anders het IP-adres
echo     van de Pi; dat vind je in de app of webpagina van je router.
echo.
pause
exit /b 1
