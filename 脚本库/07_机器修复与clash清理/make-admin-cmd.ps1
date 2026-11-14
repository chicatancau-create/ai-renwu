# RETIRED 2026-11-13 - DO NOT RUN. This v1 generator emitted the dangerous
# "recursive file count == 0 -> Remove-Item -Recurse -Force" logic, where the count
# came from -ErrorAction SilentlyContinue (swallows ACL denials -> false 0 -> would
# delete an unreadable directory). Running it would OVERWRITE the safe
# fix-admin-items.cmd produced by make-admin-cmd-v2.ps1 and reintroduce that logic.
# Kept below for history only; the guard makes it inert.
Write-Output 'RETIRED: make-admin-cmd.ps1 (v1) is disabled - it would regenerate the unsafe auto-delete .cmd.'
Write-Output 'Use instead: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\07_机器修复与clash清理\make-admin-cmd-v2.ps1'
exit 0

$ErrorActionPreference = 'Stop'
$lines = @(
'@echo off',
'setlocal',
'REM One-click fix for two admin-only items: Radmin InterfaceMetric + empty clash residual.',
'REM Double-click and accept the UAC prompt. Reversible; does NOT disable any adapter.',
'fltmc >nul 2>&1',
'if %errorlevel%==0 goto :admin',
'if "%DSH_ADMIN_FIX_ELEVATED%"=="1" (',
'  echo Elevation was cancelled or failed. Nothing changed.',
'  pause',
'  exit /b 1',
')',
'set DSH_ADMIN_FIX_ELEVATED=1',
'echo Requesting administrator rights...',
'powershell -NoProfile -Command "Start-Process -FilePath ''%~f0'' -Verb RunAs"',
'exit /b 0',
':admin',
'echo === 1. Set Radmin InterfaceMetric to 5000 ===',
'powershell -NoProfile -Command "$ra = Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like ''*Radmin*'' }; if ($ra) { Set-NetIPInterface -InterfaceIndex $ra.InterfaceIndex -InterfaceMetric 5000; Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like ''*Radmin*'' } | Select-Object InterfaceIndex,InterfaceMetric | Format-Table | Out-String | Write-Host; $f = Find-NetRoute -RemoteIPAddress 8.8.8.8 -ErrorAction SilentlyContinue; if ($f) { Write-Host (''egress: '' + $f[0].IPAddress + '' ifIndex='' + $f[0].InterfaceIndex) } } else { Write-Host ''Radmin interface not found'' }"',
'echo === 2. Remove empty clash-verge-service residual ===',
'powershell -NoProfile -Command "$p=''C:\ProgramData\clash-verge-service''; if (Test-Path $p) { $f=@(Get-ChildItem $p -Recurse -Force -File -ErrorAction SilentlyContinue); if ($f.Count -eq 0) { Remove-Item $p -Recurse -Force; Write-Host (''removed, exists='' + (Test-Path $p)) } else { Write-Host ''SKIP: dir not empty'' } } else { Write-Host ''already gone'' }"',
'echo === DONE ===',
'pause'
)
$text = ($lines -join "`r`n") + "`r`n"
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'fix-admin-items.cmd'), $text, [System.Text.Encoding]::ASCII)
Write-Output ('written: ' + (Get-Item (Join-Path $PSScriptRoot 'fix-admin-items.cmd')).Length + ' bytes')
