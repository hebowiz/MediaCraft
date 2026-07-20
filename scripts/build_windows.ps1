$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$libmpvDll = Join-Path $projectRoot "vendor\mpv\libmpv-2.dll"

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw "Virtual environment not found. Run: python -m venv .venv"
}
if (-not (Test-Path -LiteralPath $libmpvDll -PathType Leaf)) {
    throw "libmpv-2.dll not found. Run: .venv\Scripts\python.exe scripts\setup_mpv.py"
}

Push-Location $projectRoot
try {
    & $pythonExe -m PyInstaller --noconfirm --clean MediaCraft.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }
}
finally {
    Pop-Location
}

Write-Host "Build complete: dist\MediaCraft\MediaCraft.exe"
