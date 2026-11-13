$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:GIT_TERMINAL_PROMPT = '0'
$cw = 'G:\CodeWeave'
$br = 'codex/project-layout-20261106'

$gp = Get-Process -Name git -ErrorAction SilentlyContinue
if ($gp) { Write-Output 'ABORT: git process running (parallel session?)'; exit 1 }

Write-Output '=== fresh status ==='
$st = git -C $cw -c core.quotepath=false status --porcelain
Write-Output ("entries=" + @($st).Count)
if (@($st).Count -eq 0) { Write-Output 'ABORT: nothing to commit'; exit 1 }

git -C $cw add -A 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: add'; exit 1 }

$staged = git -C $cw -c core.quotepath=false diff --cached --name-only
Write-Output ("staged files=" + @($staged).Count)
$logs = $staged | Where-Object { "$_" -match '\.log$' }
if ($logs) { Write-Output 'ABORT: log files staged (ignore rule broken):'; $logs | ForEach-Object { Write-Output "$_" }; exit 1 }
$sum = 0
foreach ($f in $staged) { $it = Get-Item -LiteralPath (Join-Path $cw $f) -ErrorAction SilentlyContinue; if ($it) { $sum += $it.Length } }
Write-Output ("staged MB=" + [math]::Round($sum/1MB,2))

git -C $cw commit -F 'G:\AIrenwu\msg-cw.txt' 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: commit'; exit 1 }
git -C $cw log --oneline -2 | ForEach-Object { "$_" }
$left = git -C $cw -c core.quotepath=false status --porcelain
if ($left) { Write-Output 'WARN leftovers:'; $left | ForEach-Object { Write-Output "$_" } } else { Write-Output 'status clean' }

Write-Output '=== push gitcode (GitCode, direct) ==='
git -C $cw -c credential.interactive=false push gitcode $br 2>&1 | ForEach-Object { "$_" }
$rcG = $LASTEXITCODE
Write-Output ("gitcode push rc=" + $rcG)

Write-Output '=== push origin (GitHub, via configured proxy) ==='
git -C $cw -c credential.interactive=false push origin $br 2>&1 | ForEach-Object { "$_" }
$rcO = $LASTEXITCODE
Write-Output ("origin push rc=" + $rcO)

Write-Output '=== verify remote heads ==='
$head = git -C $cw rev-parse HEAD
Write-Output ("local HEAD=" + $head)
git -C $cw ls-remote gitcode "refs/heads/$br" 2>&1 | ForEach-Object { Write-Output ("gitcode: " + $_) }
git -C $cw -c credential.interactive=false ls-remote origin "refs/heads/$br" 2>&1 | ForEach-Object { Write-Output ("origin: " + $_) }
if ($rcG -ne 0 -or $rcO -ne 0) { Write-Output 'PUSH INCOMPLETE'; exit 1 }
Write-Output '=== CODEWEAVE DONE ==='
exit 0
