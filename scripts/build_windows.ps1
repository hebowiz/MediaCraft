$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$libmpvDll = Join-Path $projectRoot "vendor\mpv\libmpv-2.dll"
$licenseFile = Join-Path $projectRoot "LICENSE"
$noticesFile = Join-Path $projectRoot "THIRD_PARTY_NOTICES.md"
$licenseDirectory = Join-Path $projectRoot "LICENSES"

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw "Virtual environment not found. Run: python -m venv .venv"
}
if (-not (Test-Path -LiteralPath $libmpvDll -PathType Leaf)) {
    throw "libmpv-2.dll not found. Run: .venv\Scripts\python.exe scripts\setup_mpv.py"
}
foreach ($requiredPath in @($licenseFile, $noticesFile, $licenseDirectory)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "License material not found: $requiredPath. Run: .venv\Scripts\python.exe scripts\collect_licenses.py"
    }
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

$distributionRoot = Join-Path $projectRoot "dist\MediaCraft"
Copy-Item -LiteralPath $licenseFile -Destination $distributionRoot -Force
Copy-Item -LiteralPath $noticesFile -Destination $distributionRoot -Force
Copy-Item -LiteralPath $licenseDirectory -Destination $distributionRoot -Recurse -Force

foreach ($relativePath in @("LICENSE", "THIRD_PARTY_NOTICES.md", "LICENSES\GPL-3.0.txt")) {
    $packagedPath = Join-Path $distributionRoot $relativePath
    if (-not (Test-Path -LiteralPath $packagedPath -PathType Leaf)) {
        throw "License material was not packaged: $packagedPath"
    }
}

Write-Host "Build complete: dist\MediaCraft\MediaCraft.exe"
