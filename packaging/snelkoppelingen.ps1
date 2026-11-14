# Maakt de snelkoppeling "Mijn Archief" op het bureaublad en in het Startmenu,
# met het eigen pictogram. Wordt aangeroepen door "Mijn Archief installeren.bat".
param([Parameter(Mandatory = $true)][string]$AppDir)

$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject WScript.Shell
$folders = @(
    [Environment]::GetFolderPath('Desktop'),
    [Environment]::GetFolderPath('Programs')
)
foreach ($folder in $folders) {
    if (-not $folder) { continue }
    $link = $shell.CreateShortcut((Join-Path $folder 'Mijn Archief.lnk'))
    $link.TargetPath = Join-Path $AppDir '.venv\Scripts\pythonw.exe'
    $link.Arguments = '"' + (Join-Path $AppDir 'main.py') + '"'
    $link.WorkingDirectory = $AppDir
    $link.IconLocation = (Join-Path $AppDir 'assets\icon.ico') + ',0'
    $link.Description = 'Mijn Archief - offline documentenarchief'
    $link.Save()
}
