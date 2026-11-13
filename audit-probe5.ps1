$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function TP($p) {
  if (Test-Path -LiteralPath $p) { 'OK   ' + $p } else { 'MISS ' + $p }
}

'=== 1. WorkBuddy installs (drift #4) ==='
TP 'D:\WorkBuddyAI\WorkBuddy.exe'
TP 'D:\WorkBuddyAIgouji\WorkBuddy.exe'
TP 'D:\WorkBuddyAIgouji\WorkBuddyAI.exe'
TP 'D:\WorkBuddyAIguonei\WorkBuddy.exe'
foreach ($exe in @('D:\WorkBuddyAI\WorkBuddy.exe','D:\WorkBuddyAIgouji\WorkBuddy.exe','D:\WorkBuddyAIguonei\WorkBuddy.exe')) {
  if (Test-Path -LiteralPath $exe) {
    $vi = (Get-Item -LiteralPath $exe).VersionInfo
    $exe + ' | FileVersion=' + $vi.FileVersion + ' | ProductVersion=' + $vi.ProductVersion
  }
}

'=== 2. WorkBuddy data dirs (drift #11) + cache path (anomaly #2) ==='
TP 'C:\Users\Admin\.workbuddy\workbuddy.db'
TP 'C:\Users\Admin\.workbuddy\app\app-config.json'
TP 'C:\Users\Admin\.workbuddy-ai\skills'
TP 'C:\Users\Admin\.workbuddy-ai\skills\.skill-list-cache.json'
TP 'C:\Users\Admin\.workbuddy-ai\.skill-list-cache.json'
TP 'C:\Users\Admin\.workbuddy-ai\skills\local-ai-handbook\SKILL.md'
TP 'C:\Users\Admin\.workbuddy-ai\skills\.disable_to_model_invocation_migration.json'

'=== 3. .dsh workbuddy json leftovers (drift #10) ==='
$left = Get-ChildItem 'C:\Users\Admin\.dsh' -Filter '.workbuddy*' -Force -ErrorAction SilentlyContinue
if ($left) { $left | ForEach-Object { 'FOUND ' + $_.FullName } } else { 'NONE (all moved away)' }
TP 'C:\Users\Admin\.dsh\.credentials.yaml'

'=== 4. project dir rename (drift #12), dynamic enumeration, no CJK literals ==='
Get-ChildItem 'G:\AIrenwu' -Directory -Filter '2026-10-10_*' | ForEach-Object {
  $root = $_.FullName
  'DIR ' + $root
  Get-ChildItem -Path (Join-Path $root '*') -Recurse -Depth 3 -Include 'watch.py','session_end.py','measure.py','register.ps1' -File -ErrorAction SilentlyContinue | ForEach-Object { '  FILE ' + $_.FullName }
}
'--- HKCU Run WindowCenter (canonical current path) ---'
$run = Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue
if ($run -and $run.WindowCenter) { $run.WindowCenter } else { 'WindowCenter Run value: NONE' }

'=== 5. DSH host + kernel pins (drift #5) ==='
TP 'D:\DeepSeek Harness\resources\app.asar'
TP 'D:\DeepSeek Harness\resources\runtime\versions.json'
TP 'D:\DeepSeek Harness\resources\app-update.yml'
$exe = 'D:\DeepSeek Harness\DeepSeek Harness.exe'
if (Test-Path -LiteralPath $exe) {
  $vi = (Get-Item -LiteralPath $exe).VersionInfo
  'DSH exe | FileVersion=' + $vi.FileVersion + ' | ProductVersion=' + $vi.ProductVersion
}
'--- runtime versions.json ---'
if (Test-Path -LiteralPath 'D:\DeepSeek Harness\resources\runtime\versions.json') {
  Get-Content -LiteralPath 'D:\DeepSeek Harness\resources\runtime\versions.json' -Raw
}
'--- profile pnpm-workspace.yaml (current kernel pins) ---'
if (Test-Path -LiteralPath 'C:\Users\Admin\.dsh\profiles\desktop\pnpm-workspace.yaml') {
  Get-Content -LiteralPath 'C:\Users\Admin\.dsh\profiles\desktop\pnpm-workspace.yaml' -Raw
}
'--- guard sync.log tail ---'
if (Test-Path -LiteralPath 'C:\Users\Admin\.dsh\guard\sync.log') {
  Get-Content -LiteralPath 'C:\Users\Admin\.dsh\guard\sync.log' -Tail 12
} else { 'sync.log MISS' }

'=== 6. runtimes (drift #8) ==='
if (Test-Path -LiteralPath 'D:\PyCharm\Python\python.exe') { & 'D:\PyCharm\Python\python.exe' --version 2>&1 }
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) { 'node on PATH: ' + $nodeCmd.Source; node --version 2>&1 } else { 'node NOT on PATH' }
TP 'D:\uv\bin\memsearch.exe'

'=== 7. cc-switch presence ==='
TP 'C:\Users\Admin\.cc-switch\cc-switch.db'
TP 'C:\Users\Admin\.cc-switch\live-state.json'
$p = Get-Process -Name 'cc-switch' -ErrorAction SilentlyContinue
if ($p) { 'cc-switch process RUNNING pid=' + ($p.Id -join ',') } else { 'cc-switch process: NONE' }
$c = Get-NetTCPConnection -LocalPort 15721 -ErrorAction SilentlyContinue
if ($c) { $c | Select-Object -First 3 LocalAddress,LocalPort,State,OwningProcess | Format-Table | Out-String } else { 'port 15721: no connections' }

'=== 8. clash verge service vs FlClash (drift #1, anomaly #3) ==='
$svc = Get-Service -Name '*clash*' -ErrorAction SilentlyContinue
if ($svc) { $svc | ForEach-Object { 'SVC ' + $_.Name + ' | ' + $_.Status + ' | ' + $_.StartType } } else { 'no *clash* service' }
TP 'D:\Clash Verge\clash-verge.exe'
TP 'D:\FlClash\FlClash.exe'
TP 'D:\FlClash\FlClashCore.exe'
TP 'C:\ProgramData\clash-verge-service'

'=== 9. misc tool paths ==='
TP 'D:\HBuilderX.4.36.2024112612-alpha\HBuilderX\cli.exe'
TP 'E:\DeskBox'
TP 'E:\OBsidian'
TP 'D:\folia-major'
TP 'D:\Claude Code Haha'
TP 'D:\Skills\reverse-trace'
TP 'D:\Skills\reverse-wechat-miniapp'
TP 'D:\QoderToolkit\ppt-master'
TP 'C:\Users\Admin\.qoder\skills'
TP 'C:\Users\Admin\.qoder\bin\git\bin\bash.exe'
$h = Get-ChildItem 'H:\*\06-skill-mcp-3.0' -Directory -ErrorAction SilentlyContinue
if ($h) { $h | ForEach-Object { 'OK   ' + $_.FullName } } else { 'MISS H:\*\06-skill-mcp-3.0 (dynamic)' }
TP 'C:\Users\Admin\.pi\agent\mcp.json'
Get-ChildItem 'C:\Users\Admin\Desktop' -Filter '*.cmd' -File -ErrorAction SilentlyContinue | ForEach-Object { 'DESKTOP CMD ' + $_.Name + ' | ' + $_.Length + ' bytes' }
$lnk = @(Get-ChildItem 'C:\Users\Admin\Desktop' -Filter '*.lnk' -File -ErrorAction SilentlyContinue)
'desktop lnk count: ' + $lnk.Count

'=== 10. course backend port 8090 (should be gone) ==='
$c9 = Get-NetTCPConnection -LocalPort 8090 -ErrorAction SilentlyContinue
if ($c9) { $c9 | Select-Object -First 3 LocalAddress,LocalPort,State,OwningProcess | Format-Table | Out-String } else { 'port 8090: no connections' }

'=== 11. execution policy ==='
Get-ExecutionPolicy -List | Format-Table | Out-String

'=== PROBE5 DONE ==='
