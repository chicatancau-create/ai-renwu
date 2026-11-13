$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output '=== A. WorkBuddy Run key fix ==='
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$before = (Get-ItemProperty $runKey).'WorkBuddy.WorkBuddyAI'
Write-Output ('before: ' + $before)
if (Test-Path 'D:\WorkBuddyAI\WorkBuddy.exe') {
  Set-ItemProperty -Path $runKey -Name 'WorkBuddy.WorkBuddyAI' -Value '"D:\WorkBuddyAI\WorkBuddy.exe"'
  $after = (Get-ItemProperty $runKey).'WorkBuddy.WorkBuddyAI'
  Write-Output ('after: ' + $after)
} else { Write-Output 'ABORT: target exe missing' }

Write-Output '=== B. Radmin interface metric fix ==='
try {
  $ra = Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Radmin*' }
  Write-Output ('before: ifIndex=' + $ra.InterfaceIndex + ' metric=' + $ra.InterfaceMetric)
  Set-NetIPInterface -InterfaceIndex $ra.InterfaceIndex -InterfaceMetric 5000 -ErrorAction Stop
  $ra2 = Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Radmin*' }
  Write-Output ('after: ifIndex=' + $ra2.InterfaceIndex + ' metric=' + $ra2.InterfaceMetric)
  $fnr = Find-NetRoute -RemoteIPAddress 8.8.8.8 -ErrorAction SilentlyContinue
  if ($fnr) { Write-Output ('egress check: localIP=' + $fnr[0].IPAddress + ' ifIndex=' + $fnr[0].InterfaceIndex) }
} catch { Write-Output ('Radmin metric change FAILED: ' + $_.Exception.Message) }

# RETIRED 2026-11-13: section C no longer deletes anything.
# Old logic: file count from -ErrorAction SilentlyContinue (swallows ACL denials ->
# false 0) + no *clash* service + no *clash-verge* process -> Remove-Item -Recurse.
# Both guards were unsound: the count could be a permission artifact, and *clash*
# also matches the CURRENT proxy FlClash. The residual dir was already enumerated
# under admin (30 files / 9 dirs / ~197MB) and deleted per-file by
# clash-cleanup-worker.ps1 after reference checks. Report only from now on.
Write-Output '=== C. clash-verge-service residual (REPORT ONLY, no delete) ==='
$cv = 'C:\ProgramData\clash-verge-service'
if (Test-Path $cv) {
  Write-Output 'NOTE: dir exists again (reinstall?) - inspect with clash-inspect.ps1; do NOT auto-delete'
} else { Write-Output 'not present (expected: deleted 2026-11-13, admin-verified)' }
Write-Output '=== DONE ==='
