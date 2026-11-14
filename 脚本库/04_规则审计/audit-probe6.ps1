$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

'=== 1. desktop core scripts dir content ==='
$dirs = Get-ChildItem 'G:\AIrenwu' -Directory -Filter '2026-10-10_*'
foreach ($d in $dirs) {
  'DIR ' + $d.FullName
  Get-ChildItem -LiteralPath $d.FullName -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @('watch.py','session_end.py','measure.py','doctor.py','register.ps1','unregister.ps1') } |
    ForEach-Object { '  FILE ' + $_.FullName }
  '  (top-level entries:)'
  Get-ChildItem -LiteralPath $d.FullName -ErrorAction SilentlyContinue | ForEach-Object { '  ' + $_.Name }
}

'=== 2. python processes (canonical script paths) ==='
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
  ForEach-Object { 'PID ' + $_.ProcessId + ' | ' + $_.CommandLine }

'=== 3. HKCU Run full + startup folders ==='
Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue | Format-List
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -ErrorAction SilentlyContinue | ForEach-Object { 'STARTUP ' + $_.Name }
Get-ChildItem 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp' -ErrorAction SilentlyContinue | ForEach-Object { 'STARTUP-PUBLIC ' + $_.Name }
$sh = New-Object -ComObject WScript.Shell
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Filter '*.lnk' -ErrorAction SilentlyContinue | ForEach-Object {
  $l = $sh.CreateShortcut($_.FullName)
  'STARTUP LNK ' + $_.Name + ' -> ' + $l.TargetPath + ' ' + $l.Arguments
}

'=== 4. scheduled tasks mentioning center/watch/python ==='
Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match 'center|watch|python' } | ForEach-Object { 'TASK ' + $_.TaskPath + $_.TaskName + ' | ' + $_.State }

'=== 5. real desktop path + files ==='
$desk = [Environment]::GetFolderPath('Desktop')
'Desktop resolved: ' + $desk
Get-ChildItem -LiteralPath $desk -File -ErrorAction SilentlyContinue | ForEach-Object { 'DESK ' + $_.Name + ' | ' + $_.Length }

'=== 6. DeskBox cmd files (find BIOS cmd) ==='
Get-ChildItem 'E:\DeskBox' -Recurse -Filter '*.cmd' -File -ErrorAction SilentlyContinue | ForEach-Object { 'BOXCMD ' + $_.FullName + ' | ' + $_.Length }

'=== 7. H drive + reverse toolchain backends + .pi ==='
if (Test-Path 'H:\') {
  'H:\ EXISTS'
  Get-ChildItem 'H:\' -Directory -ErrorAction SilentlyContinue | Select-Object -First 10 | ForEach-Object { 'HDIR ' + $_.Name }
} else { 'H:\ NOT PRESENT' }
foreach ($p in @('D:\CloakBrowser','D:\WMPFDebugger','D:\Camoufox','D:\FireFoxReverseAI','C:\Users\Admin\.pi','C:\Users\Admin\.pi\agent')) {
  if (Test-Path -LiteralPath $p) { 'OK   ' + $p } else { 'MISS ' + $p }
}

'=== 8. HBuilder ccgui pref.json (security item, existence only, content NOT read) ==='
$pref = Join-Path $env:APPDATA 'HBuilder X\extensions\ccgui\pref.json'
if (Test-Path -LiteralPath $pref) { 'OK   ' + $pref + ' | ' + (Get-Item -LiteralPath $pref).Length + ' bytes' } else { 'MISS ' + $pref }

'=== PROBE6 DONE ==='
