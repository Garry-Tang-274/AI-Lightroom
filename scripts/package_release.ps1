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
New-Item -ItemType Directory -Path $Stage | Out-Null
Copy-Item -LiteralPath $Source -Destination $Stage -Recurse -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE"), (Join-Path $ProjectRoot "THIRD_PARTY_NOTICES.md"), (Join-Path $ProjectRoot "README.md") -Destination $Stage
Compress-Archive -LiteralPath $Stage -DestinationPath $Zip -CompressionLevel Optimal
Write-Output "Release ZIP: $Zip"
