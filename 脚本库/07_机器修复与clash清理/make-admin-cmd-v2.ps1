# make-admin-cmd-v2.ps1 - regenerate fix-admin-items.cmd (ASCII + CRLF, no BOM).
# Changes vs v1: clash residual dir was DELETED 2026-11-13 after full enumeration + reference checks.
# Section 2 now ONLY reports existence. The old "recursive count==0 then delete" logic is retired:
# -ErrorAction SilentlyContinue swallows ACL denials -> false 0 -> the exact handbook pitfall.
# ASCII-only. Run: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\07_机器修复与clash清理\make-admin-cmd-v2.ps1
$lines = @(
  '@echo off',
  'setlocal',
  'REM One-click admin fix. Radmin InterfaceMetric already applied 2026-11-13 (idempotent re-check).',
  'REM Clash residual dir DELETED 2026-11-13 after full enumeration + reference checks (30 files, 197MB).',
  'REM Section 2 is existence-report only; the old auto-delete-on-zero-count logic is retired (ACL pitfall).',
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
  'echo === 2. Clash residual dir (deleted 2026-11-13; existence report only, NO auto-delete) ===',
  'powershell -NoProfile -Command "$p=''C:\ProgramData\clash-verge-service''; if (Test-Path $p) { Write-Host ''NOTE: dir exists again (reinstall?) - inspect manually; do NOT auto-delete'' } else { Write-Host ''not present (expected: deleted 2026-11-13, admin-verified)'' }"',
  'echo === DONE ===',
  'pause'
)
Set-Content -LiteralPath (Join-Path $PSScriptRoot 'fix-admin-items.cmd') -Value $lines -Encoding ASCII
Write-Output ('written lines = ' + $lines.Count)
Write-Output '--- readback ---'
Get-Content -LiteralPath (Join-Path $PSScriptRoot 'fix-admin-items.cmd') | ForEach-Object { Write-Output $_ }
