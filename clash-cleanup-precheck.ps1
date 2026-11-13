# clash-cleanup-precheck.ps1 - NON-ADMIN read-only reference checks before deleting
# C:\ProgramData\clash-verge-service (user approved 2026-11-13: enumerate fully, then delete)
# ASCII-only. Run: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\clash-cleanup-precheck.ps1
$ErrorActionPreference = 'Continue'
$dir = 'C:\ProgramData\clash-verge-service'

Write-Output '=== 1. target dir (non-admin view; Test-Path False is AMBIGUOUS under ACL) ==='
Write-Output ("Test-Path = " + (Test-Path -LiteralPath $dir))

Write-Output '=== 2. services whose PathName references the dir ==='
$svc = Get-CimInstance Win32_Service | Where-Object { $_.PathName -like '*clash-verge-service*' }
if ($svc) { foreach ($s in $svc) { Write-Output ("SVC " + $s.Name + " | " + $s.State + " | " + $s.PathName) } } else { Write-Output 'NONE' }
Write-Output '--- service names/display *verge* *mihomo* ---'
$svc2 = Get-Service | Where-Object { $_.Name -like '*verge*' -or $_.Name -like '*mihomo*' -or $_.DisplayName -like '*verge*' -or $_.DisplayName -like '*mihomo*' }
if ($svc2) { foreach ($s in $svc2) { Write-Output ("SVC2 " + $s.Name + " | " + $s.Status) } } else { Write-Output 'NONE' }

Write-Output '=== 3. processes with ExecutablePath under the dir (CIM sees all names) ==='
$proc = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like ($dir + '*') }
if ($proc) { foreach ($p in $proc) { Write-Output ("PROC " + $p.ProcessId + " | " + $p.ExecutablePath) } } else { Write-Output 'NONE' }
Write-Output '--- verge/mihomo process names (precise, NOT *clash* which matches FlClash) ---'
$proc2 = Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*verge*' -or $_.Name -like '*mihomo*' }
if ($proc2) { foreach ($p in $proc2) { Write-Output ("PROC2 " + $p.ProcessId + " | " + $p.Name + " | " + $p.ExecutablePath) } } else { Write-Output 'NONE' }
Write-Output '--- current proxy FlClash identity (must remain untouched) ---'
$fc = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'FlClash*' }
if ($fc) { foreach ($p in $fc) { Write-Output ("FLCLASH " + $p.ProcessId + " | " + $p.ExecutablePath) } } else { Write-Output 'FLCLASH NONE (unexpected!)' }

Write-Output '=== 4. scheduled tasks referencing the dir ==='
$hits = @()
foreach ($t in (Get-ScheduledTask)) {
  foreach ($a in $t.Actions) {
    if (($a.Execute -like '*clash-verge-service*') -or ($a.Arguments -like '*clash-verge-service*') -or ($a.WorkingDirectory -like '*clash-verge-service*')) {
      $hits += ($t.TaskPath + $t.TaskName + ' | ' + $a.Execute + ' ' + $a.Arguments)
    }
  }
}
if ($hits.Count -gt 0) { foreach ($h in $hits) { Write-Output ("TASK " + $h) } } else { Write-Output 'NONE' }

Write-Output '=== 5. Run/RunOnce registry keys referencing the dir ==='
$keys = @(
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
  'HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Run',
  'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
  'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
)
$runhits = @()
foreach ($k in $keys) {
  if (Test-Path $k) {
    $p = Get-ItemProperty -Path $k
    foreach ($prop in $p.PSObject.Properties) {
      if ($prop.Name -like 'PS*') { continue }
      if ([string]$prop.Value -like '*clash-verge-service*') { $runhits += ($k + ' | ' + $prop.Name + ' = ' + $prop.Value) }
    }
  }
}
if ($runhits.Count -gt 0) { foreach ($h in $runhits) { Write-Output ("RUN " + $h) } } else { Write-Output 'NONE' }

Write-Output '=== 6. port 7890 REAL TCP test (dual-stack listener has BLANK State; any State filter drops it) ==='
$t = Test-NetConnection -ComputerName 127.0.0.1 -Port 7890 -WarningAction SilentlyContinue
Write-Output ("7890 TcpTestSucceeded = " + $t.TcpTestSucceeded)
Write-Output 'PRECHECK DONE'
