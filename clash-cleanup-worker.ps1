# clash-cleanup-worker.ps1 - ELEVATED worker (UAC). Order: re-check refs -> full enum -> per-file delete -> typed-exception verify.
# Guards (handbook: wu-quanxian-du-ProgramData record): enum failure = ABORT (never treat denied as empty);
# any service/process/task reference = ABORT; verify gone via ItemNotFoundException vs UnauthorizedAccess.
# Port health uses REAL TCP test (Test-NetConnection). Get-NetTCPConnection: the dual-stack :: listener
# has a BLANK State column, so ANY State filter (cmdlet -State or client-side Where-Object) drops it.
# Query by -LocalPort only (entries + OwningProcess), or better: real TCP connect. Handbook record:
# cai-keng-sha-ruan-duan-wang...StateListen (2026-11-13 re-confirmed on FlClash 7890).
# ASCII-only. Results -> G:\AIrenwu\clash-cleanup-result.log
$log = 'G:\AIrenwu\clash-cleanup-result.log'
$dir = 'C:\ProgramData\clash-verge-service'
function Log([string]$m) { Add-Content -LiteralPath $log -Value $m -Encoding UTF8 }
Set-Content -LiteralPath $log -Value ('=== clash cleanup worker ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ===') -Encoding UTF8

fltmc > $null 2>&1
if ($LASTEXITCODE -ne 0) { Log 'FATAL: not admin (fltmc rc!=0) - abort, nothing touched'; exit 1 }
Log 'admin: fltmc rc=0'

# --- 1. reference re-checks (admin authoritative) ---
$abort = $false
$svc = Get-CimInstance Win32_Service | Where-Object { $_.PathName -like '*clash-verge-service*' }
if ($svc) { foreach ($s in $svc) { Log ('ABORT service ref: ' + $s.Name + ' ' + $s.PathName) }; $abort = $true } else { Log 'service PathName refs: NONE' }
$proc = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like ($dir + '*') }
if ($proc) { foreach ($p in $proc) { Log ('ABORT process under dir: ' + $p.ProcessId + ' ' + $p.ExecutablePath) }; $abort = $true } else { Log 'process ExecutablePath refs: NONE' }
$vm = Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*verge*' -or $_.Name -like '*mihomo*' }
if ($vm) { foreach ($p in $vm) { Log ('ABORT verge/mihomo process: ' + $p.ProcessId + ' ' + $p.Name) }; $abort = $true } else { Log 'verge/mihomo processes: NONE' }
$taskhits = @()
foreach ($t in (Get-ScheduledTask)) { foreach ($a in $t.Actions) { if (($a.Execute -like '*clash-verge-service*') -or ($a.Arguments -like '*clash-verge-service*')) { $taskhits += ($t.TaskPath + $t.TaskName) } } }
if ($taskhits.Count -gt 0) { foreach ($h in $taskhits) { Log ('ABORT task ref: ' + $h) }; $abort = $true } else { Log 'scheduled task refs: NONE' }
if ($abort) { Log 'FATAL: references found - DELETE SKIPPED, dir untouched'; exit 1 }

# --- 2. current proxy identity baseline (FlClash must survive) ---
$fc = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'FlClash*' })
foreach ($p in $fc) { Log ('FlClash proc: ' + $p.ProcessId + ' ' + $p.ExecutablePath) }
$t = Test-NetConnection -ComputerName 127.0.0.1 -Port 7890 -WarningAction SilentlyContinue
Log ('7890 real TCP test before delete = ' + $t.TcpTestSucceeded)

# --- 3. existence with typed discrimination ---
try { Get-Item -LiteralPath $dir -ErrorAction Stop | Out-Null }
catch [System.Management.Automation.ItemNotFoundException] { Log 'dir already gone (ItemNotFoundException) - nothing to delete'; Log 'DONE'; exit 0 }
catch { Log ('FATAL: dir state ambiguous: ' + $_.Exception.GetType().Name + ' ' + $_.Exception.Message); exit 1 }

# --- 4. full enumeration (evidence BEFORE any delete; failure = abort) ---
try {
  $files = @(Get-ChildItem -LiteralPath $dir -Recurse -Force -File -ErrorAction Stop)
  $dirs  = @(Get-ChildItem -LiteralPath $dir -Recurse -Force -Directory -ErrorAction Stop)
} catch { Log ('FATAL: ENUM FAILED (denied != empty): ' + $_.Exception.Message + ' - nothing deleted'); exit 1 }
$sum = ($files | Measure-Object -Property Length -Sum).Sum
Log ('ENUM file count = ' + $files.Count)
Log ('ENUM dir count = ' + $dirs.Count)
Log ('ENUM total bytes = ' + $sum)
try { Log ('ACL owner = ' + (Get-Acl -LiteralPath $dir).Owner) } catch { Log ('ACL owner unreadable: ' + $_.Exception.Message) }
foreach ($d in $dirs)  { Log ('DIR  ' + $d.FullName) }
foreach ($f in $files) { Log ('FILE ' + $f.FullName + ' | ' + $f.Length + ' B | mtime ' + $f.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')) }

# --- 5. per-file delete (user approved after full enumeration) ---
$fail = 0
foreach ($f in $files) {
  try { Remove-Item -LiteralPath $f.FullName -Force -ErrorAction Stop; Log ('DEL OK ' + $f.FullName) }
  catch { $fail++; Log ('DEL FAIL ' + $f.FullName + ' | ' + $_.Exception.Message) }
}
foreach ($d in ($dirs | Sort-Object { $_.FullName.Length } -Descending)) {
  try { Remove-Item -LiteralPath $d.FullName -Force -ErrorAction Stop; Log ('DELDIR OK ' + $d.FullName) }
  catch { $fail++; Log ('DELDIR FAIL ' + $d.FullName + ' | ' + $_.Exception.Message) }
}
if ($fail -gt 0) { Log ('FATAL: ' + $fail + ' items failed - root kept for inspection'); exit 1 }
try { Remove-Item -LiteralPath $dir -Force -ErrorAction Stop; Log 'DEL ROOT OK' }
catch { Log ('FATAL: DEL ROOT FAIL ' + $_.Exception.Message); exit 1 }

# --- 6. verify gone: typed exception (admin view; denied != gone) ---
try {
  Get-Item -LiteralPath $dir -ErrorAction Stop | Out-Null
  Log 'VERIFY FAIL: dir still exists after delete'; exit 1
} catch [System.Management.Automation.ItemNotFoundException] {
  Log 'VERIFY OK: ItemNotFoundException - truly gone (admin view)'
} catch {
  Log ('VERIFY AMBIGUOUS: ' + $_.Exception.GetType().Name + ' ' + $_.Exception.Message); exit 1
}

# --- 7. proxy still alive after delete ---
$fc2 = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'FlClash*' })
Log ('FlClash procs after delete = ' + $fc2.Count)
$t2 = Test-NetConnection -ComputerName 127.0.0.1 -Port 7890 -WarningAction SilentlyContinue
Log ('7890 real TCP test after delete = ' + $t2.TcpTestSucceeded)
Log 'DONE'
exit 0
