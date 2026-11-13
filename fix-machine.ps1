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

Write-Output '=== C. clash-verge-service residual cleanup ==='
$cv = 'C:\ProgramData\clash-verge-service'
if (Test-Path $cv) {
  $items = @(Get-ChildItem $cv -Recurse -Force -ErrorAction SilentlyContinue)
  $files = @($items | Where-Object { -not $_.PSIsContainer })
  Write-Output ('total items=' + $items.Count + ' files=' + $files.Count)
  $svc = Get-Service | Where-Object { $_.Name -like '*clash*' }
  $procs = Get-Process | Where-Object { $_.Path -like '*clash-verge*' }
  if ($files.Count -eq 0 -and -not $svc -and -not $procs) {
    try {
      Remove-Item $cv -Recurse -Force -ErrorAction Stop
      Write-Output ('removed; still exists=' + (Test-Path $cv))
    } catch { Write-Output ('removal FAILED: ' + $_.Exception.Message) }
  } else { Write-Output 'SKIP removal: not confirmed empty/orphaned' }
} else { Write-Output 'dir already gone' }
Write-Output '=== DONE ==='
