param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $ProjectRoot "dist\AI Lightroom"
$Script = Join-Path $ProjectRoot "packaging\AI-Lightroom.iss"
$Installer = Join-Path $ProjectRoot ("releases\AI-Lightroom-" + $Version + "-Setup.exe")

if (-not (Test-Path -LiteralPath (Join-Path $Source "AI Lightroom.exe"))) {
    throw "Build output not found. Run scripts\\build_windows.ps1 first."
}
if (-not (Test-Path -LiteralPath $Script)) {
    throw "Inno Setup script not found: $Script"
}

$Candidates = @(
    (Get-Command "ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$Compiler = $Candidates | Select-Object -First 1
if (-not $Compiler) {
    throw "Inno Setup 6 was not found. Install JRSoftware.InnoSetup, then run this script again."
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Installer) | Out-Null
if (Test-Path -LiteralPath $Installer) {
    throw "Refusing to overwrite an existing installer: $Installer. Choose a new version or archive the existing artifact first."
}
& $Compiler ("/DMyAppVersion=" + $Version) $Script
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Installer)) {
    throw "Inno Setup did not produce the expected installer: $Installer"
}
Write-Output "Installer: $Installer"
