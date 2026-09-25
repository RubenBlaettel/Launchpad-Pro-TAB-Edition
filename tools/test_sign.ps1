<#
.SYNOPSIS
  Signiert Dateien mit einem selbst erstellten Test-Zertifikat.

.DESCRIPTION
  Nur fuer das CI: prueft den kompletten Signierablauf (tools/signing.py, zwei Inno-Durchlaeufe,
  signierte PyInstaller-EXE) bei jedem Lauf - ohne SignPath. Die Signatur ist NICHT
  vertrauenswuerdig und darf nie veroeffentlicht werden (Releases signiert SignPath).
  Laeuft unter Windows PowerShell 5.1 (New-SelfSignedCertificate) - daher nur ASCII in dieser Datei.

.PARAMETER Pfad
  Dateien oder Ordner (Platzhalter erlaubt); Ordner werden ohne Unterordner signiert.
#>
param([Parameter(Mandatory = $true)][string[]]$Pfad)

$ErrorActionPreference = "Stop"
$subject = "CN=Launchpad Pro TAB Test (nicht vertrauenswuerdig)"
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object Subject -eq $subject | Select-Object -First 1
if (-not $cert) {
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
        -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddDays(2)
}

$files = @(foreach ($p in $Pfad) { Get-ChildItem -Path $p -File })
if ($files.Count -eq 0) { throw "Keine Dateien zum Signieren gefunden: $Pfad" }
foreach ($f in $files) {
    $result = Set-AuthenticodeSignature -FilePath $f.FullName -Certificate $cert -HashAlgorithm SHA256
    if (-not (Get-AuthenticodeSignature -FilePath $f.FullName).SignerCertificate) {
        throw "Nicht signiert: $($f.FullName) - $($result.StatusMessage)"
    }
}
Write-Host "$($files.Count) Datei(en) mit dem Test-Zertifikat signiert."
