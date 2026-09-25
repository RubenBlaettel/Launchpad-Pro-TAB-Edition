<#
.SYNOPSIS
  Prüft den Windows-Installer von Launchpad Pro TAB Edition von vorne bis hinten.

.DESCRIPTION
  Wird im CI (GitHub Actions, Windows) ausgeführt – kann aber auch auf einem Test-PC mit
  Administratorrechten laufen. Ablauf:
    1. Stille Installation nach C:\Program Files -> Dateien, Verknüpfungen, Registry prüfen
    2. Installiertes Programm: --smoke-test
    3. Update-Szenario: Programm läuft, Installer wartet (LPTABWAITPID), ersetzt die
       Dateien und startet das Programm danach neu (LPTABRESTART=1)
    4. Stille Deinstallation mit LPTABPURGE=1 -> Programm, Verknüpfungen, Registry,
       Einstellungen und Projekte sind entfernt

.PARAMETER Setup
  Pfad zur LaunchpadProTAB-Setup-<version>.exe
#>
param([Parameter(Mandatory = $true)][string]$Setup)

$ErrorActionPreference = "Stop"
$AppName = "Launchpad Pro TAB Edition"
$AppDir = Join-Path $env:ProgramFiles $AppName
$Exe = Join-Path $AppDir "LaunchpadProTAB.exe"
$UninstallKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{623A59DC-8E1B-496A-A80C-66ADADD7D898}_is1"
$Logs = Join-Path $env:RUNNER_TEMP "installer-logs"
if (-not $env:RUNNER_TEMP) { $Logs = Join-Path $env:TEMP "installer-logs" }
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
# Das Programm soll im Test nie GitHub abfragen und ohne Bildschirm laufen
$env:LPTAB_UPDATE_URL = "http://127.0.0.1:9/keine-updates"
$env:QT_QPA_PLATFORM = "offscreen"

function Assert($Condition, $Message) {
    if (-not $Condition) { throw "PRÜFUNG FEHLGESCHLAGEN: $Message" }
    Write-Host "  ok: $Message"
}

function Run-Setup([string[]]$Arguments, [string]$LogName) {
    $log = Join-Path $Logs $LogName
    $p = Start-Process -FilePath $Setup -ArgumentList ($Arguments + "/LOG=`"$log`"") -Wait -PassThru
    Write-Host "  Installer beendet mit Code $($p.ExitCode) (Protokoll: $log)"
    return $p.ExitCode
}

Write-Host "== 1. Stille Erstinstallation"
$code = Run-Setup @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") "1-installation.log"
Assert ($code -eq 0) "Installer-Exitcode 0"
Assert (Test-Path $Exe) "Programm liegt in $AppDir"
Assert (Test-Path (Join-Path $AppDir "unins000.exe")) "Deinstaller vorhanden"
Assert (Test-Path (Join-Path $AppDir "_internal")) "Programmbibliotheken vorhanden"
$desktop = Join-Path ([Environment]::GetFolderPath("CommonDesktopDirectory")) "$AppName.lnk"
$startmenu = Join-Path ([Environment]::GetFolderPath("CommonPrograms")) "$AppName.lnk"
Assert (Test-Path $desktop) "Desktop-Verknüpfung (Standard: an)"
Assert (Test-Path $startmenu) "Startmenü-Eintrag (Standard: an)"
$key = Get-ItemProperty -Path $UninstallKey
Assert ($key.DisplayName -eq $AppName) "Eintrag unter Apps & Features"
Write-Host "  installierte Version: $($key.DisplayVersion)"
Assert ((Get-ItemProperty "HKLM:\SOFTWARE\Classes\.lptab").'(default)' -eq "LaunchpadProTAB.Projekt") "Dateizuordnung .lptab"
Assert (Test-Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\LaunchpadProTAB.exe") "App Paths (Win+R)"

Write-Host "== 2. Installiertes Programm: Selbsttest"
$p = Start-Process -FilePath $Exe -ArgumentList "--smoke-test" -Wait -PassThru
Assert ($p.ExitCode -eq 0) "Smoke-Test des installierten Programms"

Write-Host "== 3. Update, während das Programm läuft"
$app = Start-Process -FilePath $Exe -ArgumentList "--no-update-check" -PassThru
Start-Sleep -Seconds 8
Assert (-not $app.HasExited) "Programm läuft (Instanz-Mutex aktiv)"
Get-ChildItem $AppDir -Filter "*.marker" -ErrorAction SilentlyContinue | Remove-Item
Set-Content -Path (Join-Path $AppDir "_internal\veraltet.marker") -Value "alt"
$ready = Join-Path $Logs "bereit.flag"
Remove-Item $ready -ErrorAction SilentlyContinue
$setupArgs = @("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LPTABWAITPID=$($app.Id)", "/LPTABREADY=`"$ready`"", "/LPTABRESTART=1")
$log = Join-Path $Logs "3-update.log"
$upd = Start-Process -FilePath $Setup -ArgumentList ($setupArgs + "/LOG=`"$log`"") -PassThru
$null = $upd.Handle   # nötig, damit ExitCode später verfügbar ist
for ($i = 0; $i -lt 60 -and -not (Test-Path $ready); $i++) { Start-Sleep -Seconds 1 }
Assert (Test-Path $ready) "Installer meldet Bereitschaft (LPTABREADY), bevor das Programm endet"
Start-Sleep -Seconds 3
Assert (-not $upd.HasExited) "Installer wartet auf das Beenden des Programms"
# Das Programm beendet sich beim echten Update selbst – hier simuliert
Stop-Process -Id $app.Id
$upd.WaitForExit(600000) | Out-Null
Write-Host "  Update-Installer beendet mit Code $($upd.ExitCode)"
Assert ($upd.ExitCode -eq 0) "Update-Installer-Exitcode 0"
Assert (Select-String -Path $log -Pattern "Warte auf das Beenden" -Quiet) "Installer hat auf das Programm gewartet"
Assert (-not (Test-Path (Join-Path $AppDir "_internal\veraltet.marker"))) "alte Programmbibliotheken ersetzt"
$restarted = $null
for ($i = 0; $i -lt 30 -and -not $restarted; $i++) {
    Start-Sleep -Seconds 1
    $restarted = Get-Process -Name "LaunchpadProTAB" -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $app.Id }
}
Assert ($null -ne $restarted) "Programm wurde nach dem Update neu gestartet"
$restarted | Stop-Process -Force
Start-Sleep -Seconds 3

Write-Host "== 4. Deinstallation inkl. Projekte und Einstellungen"
$cfg = Join-Path $env:APPDATA "LaunchpadProTAB"
$projRoot = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Launchpad Pro TAB"
$proj = Join-Path $projRoot "CI-Projekt"
New-Item -ItemType Directory -Force -Path (Join-Path $proj "audio") | Out-Null
Set-Content -Path (Join-Path $proj "projekt.lptab") -Encoding UTF8 -Value '{"format": "launchpad-pro-tab", "version": 1}'
New-Item -ItemType Directory -Force -Path $cfg | Out-Null
$settings = @{ recent_projects = @(@{ path = $proj; name = "CI-Projekt" }); last_project = $proj } | ConvertTo-Json -Depth 4
Set-Content -Path (Join-Path $cfg "einstellungen.json") -Encoding UTF8 -Value $settings
$uninstaller = Join-Path $AppDir "unins000.exe"
$p = Start-Process -FilePath $uninstaller -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/LPTABPURGE=1", "/LOG=`"$(Join-Path $Logs '4-deinstallation.log')`"") -Wait -PassThru
for ($i = 0; $i -lt 60 -and (Test-Path $Exe); $i++) { Start-Sleep -Seconds 1 }
Assert (-not (Test-Path $Exe)) "Programmdateien entfernt"
Assert (-not (Test-Path $desktop)) "Desktop-Verknüpfung entfernt"
Assert (-not (Test-Path $startmenu)) "Startmenü-Eintrag entfernt"
Assert (-not (Test-Path $UninstallKey)) "Eintrag unter Apps & Features entfernt"
Assert (-not (Test-Path "HKLM:\SOFTWARE\Classes\LaunchpadProTAB.Projekt")) "Dateizuordnung entfernt"
Assert (-not (Test-Path $proj)) "Projekt gelöscht (Checkbox „Alle Projekte und Einstellungen löschen“)"
Assert (-not (Test-Path $cfg)) "Einstellungen gelöscht"

Write-Host "Installer-Test erfolgreich."
