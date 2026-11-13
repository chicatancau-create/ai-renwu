$ErrorActionPreference = 'Continue'
$log = 'G:\AIrenwu\admin-fix-result.log'
$lines = @()
$lines += '=== ADMIN FIX WORKER (elevated) ==='
$lines += ('time: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$null = fltmc 2>&1
$lines += ('fltmc exit (0=admin): ' + $LASTEXITCODE)
try {
  $ra = Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Radmin*' }
  if ($ra) {
    $lines += ('Radmin before: ifIndex=' + $ra.InterfaceIndex + ' metric=' + $ra.InterfaceMetric)
    Set-NetIPInterface -InterfaceIndex $ra.InterfaceIndex -InterfaceMetric 5000 -ErrorAction Stop
    $ra2 = Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Radmin*' }
    $lines += ('Radmin after: metric=' + $ra2.InterfaceMetric)
  } else { $lines += 'Radmin interface not found' }
} catch { $lines += ('Radmin ERROR: ' + $_.Exception.Message) }
try {
  $f = Find-NetRoute -RemoteIPAddress 8.8.8.8 -ErrorAction SilentlyContinue
  if ($f) { $lines += ('egress: ' + (($f | Select-Object -First 1 | Out-String).Trim())) }
} catch { $lines += ('egress check error: ' + $_.Exception.Message) }
# RETIRED 2026-11-13: auto-delete removed from this ELEVATED worker.
# Old logic counted files with -ErrorAction SilentlyContinue, which swallows ACL
# denials -> false 0 -> would delete a directory it could not even read (handbook
# pitfall: unreadable ProgramData mistaken for empty, service core destroyed).
# The dir was fully enumerated under admin (30 files / 9 dirs / ~197MB) and deleted
# per-file by clash-cleanup-worker.ps1 after two rounds of reference checks.
# This worker now REPORTS existence only. Never delete based on a swallowed count.
try {
  $p = 'C:\ProgramData\clash-verge-service'
  if (Test-Path $p) {
    $lines += 'clash dir EXISTS AGAIN (reinstall?) - report only, NO auto-delete; inspect with clash-inspect.ps1'
  } else { $lines += 'clash dir not present (expected: deleted 2026-11-13, admin-verified)' }
} catch { $lines += ('clash ERROR: ' + $_.Exception.Message) }
$lines += '=== DONE ==='
$lines | Out-File -FilePath $log -Encoding UTF8
