; Installatieprogramma voor Mijn Archief (Inno Setup 6).
; Wordt automatisch gebouwd door .github/workflows/windows.yml.
; Installeert zonder beheerdersrechten, alleen voor de huidige gebruiker.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6E0B7C2A-3F4D-4E59-9C7B-5A1D2B8E4F10}
AppName=Mijn Archief
AppVersion={#AppVersion}
AppPublisher=Mijn Archief
DefaultDirName={autopf}\Mijn Archief
DefaultGroupName=Mijn Archief
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\Output
OutputBaseFilename=MijnArchief-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\MijnArchief.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"

[Tasks]
Name: "desktopicon"; Description: "Snelkoppeling op het bureaublad maken"; GroupDescription: "Extra:"

[Files]
Source: "..\dist\MijnArchief\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Mijn Archief"; Filename: "{app}\MijnArchief.exe"
Name: "{autodesktop}\Mijn Archief"; Filename: "{app}\MijnArchief.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MijnArchief.exe"; Description: "Mijn Archief nu starten"; Flags: nowait postinstall skipifsilent

; Let op: bij verwijderen van het programma blijft je archiefmap (met al je
; documenten) gewoon staan.
