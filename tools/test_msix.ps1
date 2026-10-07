<#
.SYNOPSIS
  Prueft das Microsoft-Store-Paket (MSIX): Testsignatur, Installation, Start, Deinstallation.

.DESCRIPTION
  Fuer das CI (Administratorrechte noetig). Das echte Paket bleibt unsigniert - der Microsoft Store
  signiert es selbst. Hier wird eine KOPIE mit einem selbst erstellten Test-Zertifikat signiert,
  dessen Herausgeber dem Manifest entspricht, damit Windows sie installiert. Ablauf:
    1. Paketname und Herausgeber aus dem Manifest lesen
    2. Test-Zertifikat anlegen, als vertrauenswuerdig eintragen, Kopie signieren (signtool)
    3. Add-AppxPackage -> Programmdatei, resources.pri, App-Alias, Dateizuordnung .lptab
    4. Programm ueber den App-Alias mit --smoke-test starten -> Bericht (LPTAB_SMOKE_REPORT):
       Code 0, Installationsart "microsoft-store", Paketfamilie gesetzt
    5. Remove-AppxPackage -> Paket und Alias entfernt, Zertifikat wieder geloescht
  Laeuft unter Windows PowerShell 5.1 (Appx-Modul, New-SelfSignedCertificate) - daher nur ASCII.

.PARAMETER Paket
  Pfad zur unsignierten LaunchpadProTAB-<version>.msix (tools/build_msix.py)
#>
param([Parameter(Mandatory = $true)][string]$Paket)

$ErrorActionPreference = "Stop"
$tmp = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$work = Join-Path $tmp "msix-test"
Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $work | Out-Null
# Das Programm soll im Test nie GitHub abfragen und ohne Bildschirm laufen
$env:LPTAB_UPDATE_URL = "http://127.0.0.1:9/keine-updates"
$env:QT_QPA_PLATFORM = "offscreen"

function Assert($Condition, $Message) {
    if (-not $Condition) { throw "PRUEFUNG FEHLGESCHLAGEN: $Message" }
    Write-Host "  ok: $Message"
}

function Find-SdkTool($Name) {
    $kits = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    $hit = Get-ChildItem $kits -Directory -Filter "10.*" -ErrorAction SilentlyContinue |
        Sort-Object { [version]$_.Name } -Descending |
        ForEach-Object { Join-Path $_.FullName "x64\$Name" } |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $hit) { throw "$Name nicht gefunden (Windows SDK)" }
    return $hit
}

function Wait-Until([scriptblock]$Condition, [int]$Seconds = 15) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return [bool](& $Condition)
}

# ---------------------------------------------------------------- 1. Manifest
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead((Resolve-Path $Paket).Path)
try {
    $reader = New-Object IO.StreamReader($zip.GetEntry("AppxManifest.xml").Open())
    [xml]$manifest = $reader.ReadToEnd()
    $reader.Close()
} finally { $zip.Dispose() }
$name = $manifest.Package.Identity.Name
$publisher = $manifest.Package.Identity.Publisher
Write-Host "Paket $name $($manifest.Package.Identity.Version), Herausgeber $publisher"
Assert ($manifest.Package.Applications.Application.Executable -eq "LaunchpadProTAB.exe") "Manifest startet LaunchpadProTAB.exe"

# ---------------------------------------------------------------- 2. Test-Signatur (nur fuer diesen Test)
$cert = New-SelfSignedCertificate -Type Custom -Subject $publisher -KeyUsage DigitalSignature `
    -FriendlyName "Launchpad Pro MSIX-Test" -CertStoreLocation Cert:\CurrentUser\My `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}") -NotAfter (Get-Date).AddDays(2)
$password = "msix-test"
$pfx = Join-Path $work "test.pfx"
$cer = Join-Path $work "test.cer"
Export-PfxCertificate -Cert $cert -FilePath $pfx -Password (ConvertTo-SecureString $password -AsPlainText -Force) | Out-Null
Export-Certificate -Cert $cert -FilePath $cer | Out-Null
Import-Certificate -FilePath $cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople | Out-Null
$signed = Join-Path $work "test.msix"
Copy-Item $Paket $signed
$signtool = Find-SdkTool "signtool.exe"
& $signtool sign /q /fd SHA256 /f $pfx /p $password $signed
if ($LASTEXITCODE -ne 0) { throw "signtool meldet Code $LASTEXITCODE" }
Write-Host "  ok: Kopie mit Test-Zertifikat signiert"

try {
    # ------------------------------------------------------------ 3. Installation
    try {
        Add-AppxPackage -Path $signed
    } catch {
        Get-AppxLog -All -ErrorAction SilentlyContinue | Select-Object -First 30 | Format-List | Out-String | Write-Host
        throw
    }
    $pkg = Get-AppxPackage -Name $name
    Assert ($null -ne $pkg) "Paket installiert ($($pkg.PackageFullName))"
    Assert (Test-Path (Join-Path $pkg.InstallLocation "LaunchpadProTAB.exe")) "Programmdatei im Paket"
    Assert (Test-Path (Join-Path $pkg.InstallLocation "_internal")) "Programmbibliotheken im Paket"
    Assert (Test-Path (Join-Path $pkg.InstallLocation "resources.pri")) "Bildvarianten (resources.pri)"
    $alias = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\LaunchpadProTAB.exe"
    Assert (Wait-Until { Test-Path $alias }) "App-Alias LaunchpadProTAB.exe angelegt"
    $progids = "Registry::HKEY_CURRENT_USER\Software\Classes\.lptab\OpenWithProgids"
    if (Wait-Until { Test-Path $progids } 10) {
        Write-Host "  ok: Dateizuordnung .lptab registriert"
    } else {
        Write-Host "  Hinweis: Dateizuordnung .lptab (noch) nicht in der Registry sichtbar"
    }

    # ------------------------------------------------------------ 4. Start im Paket
    $report = Join-Path $work "smoke.json"
    $env:LPTAB_SMOKE_REPORT = $report
    $p = Start-Process -FilePath $alias -ArgumentList "--smoke-test" -PassThru
    $null = $p.Handle
    if (-not $p.WaitForExit(240000)) { $p.Kill(); throw "Smoke-Test im Paket haengt (4 min)" }
    Remove-Item Env:\LPTAB_SMOKE_REPORT
    Assert (Test-Path $report) "Smoke-Test-Bericht geschrieben (Prozess-Code $($p.ExitCode))"
    $text = Get-Content $report -Raw
    Write-Host "  Bericht: $text"
    $r = $text | ConvertFrom-Json
    Assert ($r.code -eq 0) "Smoke-Test im Paket erfolgreich"
    Assert ($r.install_kind -eq "microsoft-store") "Programm erkennt die Store-Fassung (keine eigenen Updates)"
    Assert ($r.package_family -like "$name*") "Paketfamilie $($r.package_family)"

    # ------------------------------------------------------------ 5. Deinstallation
    Remove-AppxPackage -Package $pkg.PackageFullName
    Assert ($null -eq (Get-AppxPackage -Name $name)) "Paket deinstalliert"
    Assert (Wait-Until { -not (Test-Path $alias) }) "App-Alias entfernt"
} finally {
    Get-AppxPackage -Name $name -ErrorAction SilentlyContinue | Remove-AppxPackage -ErrorAction SilentlyContinue
    Remove-Item "Cert:\LocalMachine\TrustedPeople\$($cert.Thumbprint)" -ErrorAction SilentlyContinue
    Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -ErrorAction SilentlyContinue
}
Write-Host "Store-Paket: alle Pruefungen bestanden."
