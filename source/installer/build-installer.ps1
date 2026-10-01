param(
    [string]$ISCC = 'ISCC.exe',
    [string]$Python = 'python',
    [string]$OutputPath = (Join-Path $PSScriptRoot '../../../installers'),
    [string]$WorkPath = (Join-Path $env:TEMP 'Codex-Glass-installer')
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$outputDir = [IO.Path]::GetFullPath($OutputPath)
$stageDir = Join-Path ([IO.Path]::GetFullPath($WorkPath)) 'stage'
New-Item -ItemType Directory -Path $outputDir,$stageDir -Force | Out-Null
& $Python (Join-Path $PSScriptRoot 'download_sources.py') (Join-Path $projectRoot 'dependency-sources')
if ($LASTEXITCODE -ne 0) { throw 'Dependency source verification failed' }
# Source tree, generated guide, binary and licenses are all part of Setup.
& $Python (Join-Path $PSScriptRoot 'prepare.py') $projectRoot $stageDir
if ($LASTEXITCODE -ne 0) { throw 'Installer staging failed' }
& $ISCC ('/DProjectRoot=' + $projectRoot) ('/DStageRoot=' + $stageDir) ('/O' + $outputDir) (Join-Path $PSScriptRoot 'Codex-Glass.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
$installer = Join-Path $outputDir 'Codex-Glass-3.1.1-Windows-x64-Setup.exe'
$checksum = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText(($installer + '.sha256'), $checksum + '  ' + (Split-Path $installer -Leaf) + "`n", [Text.UTF8Encoding]::new($false))
Write-Output $installer
