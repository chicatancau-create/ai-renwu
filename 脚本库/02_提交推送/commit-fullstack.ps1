$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:GIT_TERMINAL_PROMPT = '0'
$p = 'E:\fullstack-code'
$msg = $PSScriptRoot

Write-Output '=== c1: .gitignore ==='
git -C $p add .gitignore 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: add gitignore'; exit 1 }
git -C $p commit -F "$msg\msg-fs-1.txt" 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: commit1'; exit 1 }

Write-Output '=== c2: Web/node ==='
git -C $p add Web/node 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: add Web/node'; exit 1 }
git -C $p commit -F "$msg\msg-fs-2.txt" 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: commit2'; exit 1 }

Write-Output '=== c3: Harmony (verify pages not empty) ==='
git -C $p add Harmony 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: add Harmony'; exit 1 }
$ns = git -C $p -c core.quotepath=false diff --cached --numstat
$pages = $ns | Where-Object { "$_" -match 'RegPage\.ets|DialogPage\.ets' }
foreach ($l in $pages) { Write-Output ("staged: " + $l) }
$bad = $pages | Where-Object { "$_" -match '^0\s' }
if ($bad -or @($pages).Count -lt 2) { Write-Output 'ABORT: pages missing or empty in index'; exit 1 }
git -C $p commit -F "$msg\msg-fs-3.txt" 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: commit3'; exit 1 }

Write-Output '=== c4: wofule (uni-app) ==='
$wfile = git -C $p -c core.quotepath=false ls-files -m -o --exclude-standard | Where-Object { "$_" -match 'wofule/' } | Select-Object -First 1
if (-not $wfile) { Write-Output 'ABORT: no wofule changes found'; exit 1 }
$parts = $wfile.Split('/')
$wroot = $parts[0] + '/' + $parts[1]
Write-Output ("wofule root=" + $wroot)
git -C $p add -- $wroot 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: add wofule'; exit 1 }
git -C $p commit -F "$msg\msg-fs-4.txt" 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: commit4'; exit 1 }

Write-Output '=== c5: projects evidence ==='
git -C $p add projects 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: add projects'; exit 1 }
git -C $p commit -F "$msg\msg-fs-5.txt" 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { Write-Output 'FAIL: commit5'; exit 1 }

Write-Output '=== post-commit status (must be empty) ==='
$left = git -C $p -c core.quotepath=false status --porcelain
if ($left) { Write-Output 'ABORT: leftovers:'; $left | ForEach-Object { Write-Output "$_" }; exit 1 }
Write-Output 'clean'
git -C $p log --oneline -6 | ForEach-Object { "$_" }

Write-Output '=== push atomgit (GitCode, direct) ==='
git -C $p -c credential.interactive=false push atomgit main 2>&1 | ForEach-Object { "$_" }
$rcA = $LASTEXITCODE
Write-Output ("atomgit push rc=" + $rcA)

Write-Output '=== push origin (GitHub, via configured proxy) ==='
git -C $p -c credential.interactive=false push origin main 2>&1 | ForEach-Object { "$_" }
$rcO = $LASTEXITCODE
Write-Output ("origin push rc=" + $rcO)

Write-Output '=== verify remote heads ==='
$head = git -C $p rev-parse HEAD
Write-Output ("local HEAD=" + $head)
git -C $p ls-remote atomgit refs/heads/main 2>&1 | ForEach-Object { Write-Output ("atomgit: " + $_) }
git -C $p -c credential.interactive=false ls-remote origin refs/heads/main 2>&1 | ForEach-Object { Write-Output ("origin: " + $_) }
if ($rcA -ne 0 -or $rcO -ne 0) { Write-Output 'PUSH INCOMPLETE'; exit 1 }
Write-Output '=== FULLSTACK DONE ==='
exit 0
