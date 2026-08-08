param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $ProjectRoot "dist\AI Lightroom"
$ReleaseRoot = Join-Path $ProjectRoot "releases"
$Stage = Join-Path $ReleaseRoot ("AI-Lightroom-" + $Version + "-windows-x64")
$Zip = $Stage + ".zip"

if (-not (Test-Path -LiteralPath $Source)) {
    throw "Build output not found. Run scripts\\build_windows.ps1 first."
}

New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null
if (Test-Path -LiteralPath $Stage) {
    throw "Release staging directory already exists: $Stage"
}
if (Test-Path -LiteralPath $Zip) {
    throw "Refusing to overwrite an existing release ZIP: $Zip. Archive it or choose a new version first."
}
New-Item -ItemType Directory -Path $Stage | Out-Null
Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Stage -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE"), (Join-Path $ProjectRoot "THIRD_PARTY_NOTICES.md"), (Join-Path $ProjectRoot "README.md"), (Join-Path $ProjectRoot "README_zh-CN.md") -Destination $Stage
Copy-Item -LiteralPath (Join-Path $ProjectRoot "docs") -Destination (Join-Path $Stage "docs") -Recurse -Force
# Archive the *contents* of the staging directory.  This lets recipients
# extract the ZIP and run ``AI Lightroom.exe`` directly from the extraction
# root instead of discovering an accidental extra wrapper directory.
$ArchiveItems = Get-ChildItem -LiteralPath $Stage -Force | Select-Object -ExpandProperty FullName
Compress-Archive -LiteralPath $ArchiveItems -DestinationPath $Zip -CompressionLevel Optimal
Write-Output "Release ZIP: $Zip"
