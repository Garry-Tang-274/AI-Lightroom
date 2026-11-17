$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment not found. Create .venv and install requirements first."
}

& $Python (Join-Path $ProjectRoot "build_tools\create_icon.py")
if ($LASTEXITCODE -ne 0) { throw "Icon build failed." }
& $Python -m pytest -q (Join-Path $ProjectRoot "tests")
if ($LASTEXITCODE -ne 0) { throw "Tests failed. No release will be built." }
& $Python -m PyInstaller --noconfirm --clean (Join-Path $ProjectRoot "ai_lightroom.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$Executable = Join-Path $ProjectRoot "dist\AI Lightroom\AI Lightroom.exe"
if (-not (Test-Path -LiteralPath $Executable)) {
    throw "Packaging completed without the expected executable."
}
Write-Output "Built: $Executable"

