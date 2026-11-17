$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    # GitHub Actions uses setup-python rather than a project-local .venv.
    $Python = (Get-Command python -ErrorAction Stop).Source
}

Push-Location -LiteralPath $ProjectRoot
try {
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

$CheckDirectory = Join-Path $ProjectRoot "temp\package-check"
New-Item -ItemType Directory -Path $CheckDirectory -Force | Out-Null
$StartupLog = Join-Path $CheckDirectory "startup-error.log"
$PreviousStartupLog = $env:AI_LIGHTROOM_STARTUP_LOG
$env:AI_LIGHTROOM_STARTUP_LOG = $StartupLog
try {
    foreach ($Arguments in @('--package-self-check', ('--smoke-test "' + (Join-Path $CheckDirectory 'smoke.png') + '"'))) {
        $Process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
        if (-not $Process.WaitForExit(60000)) {
            # Only stop the exact validation process created by this script.
            $Process.Kill()
            $Process.WaitForExit()
            throw "Packaged application validation timed out: $Arguments. See $StartupLog"
        }
        if ($Process.ExitCode -ne 0) {
            if (Test-Path -LiteralPath $StartupLog) { Get-Content -LiteralPath $StartupLog | Write-Output }
            throw "Packaged application failed validation (exit $($Process.ExitCode)): $Arguments"
        }
    }
} finally {
    $env:AI_LIGHTROOM_STARTUP_LOG = $PreviousStartupLog
}
Write-Output "Built and startup-verified: $Executable"
} finally {
    Pop-Location
}

