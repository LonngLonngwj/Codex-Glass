param([string]$Python = 'python', [string]$WorkPath = (Join-Path $env:TEMP 'Codex-Glass-build'))
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$workDir = $WorkPath
$distDir = Join-Path $projectRoot 'app'
& $Python -m PyInstaller --noconfirm --clean --windowed --onedir --name Codex-Glass --icon (Join-Path $PSScriptRoot 'assets/Codex-Glass.ico') --additional-hooks-dir (Join-Path $PSScriptRoot 'hooks') --version-file (Join-Path $PSScriptRoot 'version_info.txt') --distpath $distDir --workpath $workDir --specpath $workDir --hidden-import PyQt6.QtSvg --add-data ((Join-Path $PSScriptRoot 'Widget.qml') + ';.') --add-data ((Join-Path $PSScriptRoot 'icons') + ';icons') --add-data ((Join-Path $PSScriptRoot 'assets') + ';assets') (Join-Path $PSScriptRoot 'main.py')
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
# Qt 6.11 requires a newer VC runtime than some Python 3.12 installers bundle.
# Ship Qt's backwards-compatible runtime at the application search root so the
# bootloader cannot pre-load an older copy before importing QtCore.
$qtBin = & $Python -c "from pathlib import Path; import PyQt6; print(Path(PyQt6.__file__).parent / 'Qt6' / 'bin')"
$internal = Join-Path $distDir 'Codex-Glass/_internal'
foreach ($name in @('VCRUNTIME140.dll','VCRUNTIME140_1.dll','MSVCP140.dll','MSVCP140_1.dll','MSVCP140_2.dll')) {
    Copy-Item -LiteralPath (Join-Path $qtBin $name) -Destination (Join-Path $internal $name)
}
# Qt uses Windows' unversioned ICU entry points. A build host's Poppler/Conda
# PATH can make PyInstaller collect incompatible version-suffixed ICU instead.
# These are generated bundle files, not system files. Use Windows' own ICU.
foreach ($name in @('icuuc.dll','icudt78.dll')) {
    $generatedDll = Join-Path $internal $name
    if (Test-Path -LiteralPath $generatedDll) { Remove-Item -LiteralPath $generatedDll }
}
