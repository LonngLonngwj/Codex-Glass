# Use this launcher from a terminal hosted inside another application.
# Local WMI launches the widget outside that application's job and redirected
# filesystem context. Normal Explorer double-click and Windows logon work too.
param([switch]$EnableStartup)
$ErrorActionPreference = 'Stop'
$programPath = Join-Path $PSScriptRoot '../Codex-Glass.exe'
if (-not (Test-Path -LiteralPath $programPath)) {
    $programPath = Join-Path $PSScriptRoot '../app/Codex-Glass/Codex-Glass.exe'
}
$program = (Resolve-Path -LiteralPath $programPath).Path
$arguments = ' --watch'
if ($EnableStartup) { $arguments += ' --enable-startup' }
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{
    ShowWindow = [uint16]0
    CreateFlags = [uint32]16777216 # CREATE_BREAKAWAY_FROM_JOB (WMI host job)
}
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = ('"' + $program + '"' + $arguments)
    CurrentDirectory = (Split-Path $program)
    ProcessStartupInformation = $startup
}
if ($result.ReturnValue -ne 0) { throw "Codex-Glass 启动失败，Windows 返回代码：$($result.ReturnValue)" }
Write-Output "Codex-Glass 已交由 Windows 独立启动（PID $($result.ProcessId)）。"
