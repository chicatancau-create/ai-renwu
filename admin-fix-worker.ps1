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
try {
  $p = 'C:\ProgramData\clash-verge-service'
  if (Test-Path $p) {
    $files = @(Get-ChildItem $p -Recurse -Force -File -ErrorAction SilentlyContinue)
    if ($files.Count -eq 0) {
      Remove-Item $p -Recurse -Force -ErrorAction Stop
      $lines += ('clash dir removed, exists=' + (Test-Path $p))
    } else { $lines += ('clash dir SKIP not empty, filecount=' + $files.Count) }
  } else { $lines += 'clash dir already gone' }
} catch { $lines += ('clash ERROR: ' + $_.Exception.Message) }
$lines += '=== DONE ==='
$lines | Out-File -FilePath $log -Encoding UTF8
