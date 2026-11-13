@echo off
setlocal
REM One-click admin fix. Radmin InterfaceMetric already applied 2026-11-13 (idempotent re-check).
REM Clash residual dir is NOT empty (30 files, admin-verified) - auto-delete only if 0 files.
REM Double-click and accept the UAC prompt. Reversible; does NOT disable any adapter.
fltmc >nul 2>&1
if %errorlevel%==0 goto :admin
if "%DSH_ADMIN_FIX_ELEVATED%"=="1" (
  echo Elevation was cancelled or failed. Nothing changed.
  pause
  exit /b 1
)
set DSH_ADMIN_FIX_ELEVATED=1
echo Requesting administrator rights...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b 0
:admin
echo === 1. Set Radmin InterfaceMetric to 5000 ===
powershell -NoProfile -Command "$ra = Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Radmin*' }; if ($ra) { Set-NetIPInterface -InterfaceIndex $ra.InterfaceIndex -InterfaceMetric 5000; Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Radmin*' } | Select-Object InterfaceIndex,InterfaceMetric | Format-Table | Out-String | Write-Host; $f = Find-NetRoute -RemoteIPAddress 8.8.8.8 -ErrorAction SilentlyContinue; if ($f) { Write-Host ('egress: ' + $f[0].IPAddress + ' ifIndex=' + $f[0].InterfaceIndex) } } else { Write-Host 'Radmin interface not found' }"
echo === 2. Clash residual check (NOT empty: 30 files; auto-delete only if 0 files) ===
powershell -NoProfile -Command "$p='C:\ProgramData\clash-verge-service'; if (Test-Path $p) { $f=@(Get-ChildItem $p -Recurse -Force -File -ErrorAction SilentlyContinue); if ($f.Count -eq 0) { Remove-Item $p -Recurse -Force; Write-Host ('removed, exists=' + (Test-Path $p)) } else { Write-Host 'SKIP: dir not empty' } } else { Write-Host 'already gone' }"
echo === DONE ===
pause
