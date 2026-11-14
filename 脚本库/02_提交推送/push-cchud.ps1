$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:GIT_TERMINAL_PROMPT = '0'
$r = 'G:\cc-hud'

$st = git -C $r -c core.quotepath=false status --porcelain
if ($st) { Write-Output 'ABORT: cc-hud not clean:'; $st | ForEach-Object { Write-Output "$_" }; exit 1 }

Write-Output '=== push atomgit (GitCode, direct) ==='
git -C $r -c credential.interactive=false push atomgit main 2>&1 | ForEach-Object { "$_" }
$rcA = $LASTEXITCODE
Write-Output ("atomgit push rc=" + $rcA)

Write-Output '=== push origin (GitHub, via configured proxy) ==='
git -C $r -c credential.interactive=false push origin main 2>&1 | ForEach-Object { "$_" }
$rcO = $LASTEXITCODE
Write-Output ("origin push rc=" + $rcO)

Write-Output '=== verify remote heads ==='
$head = git -C $r rev-parse HEAD
Write-Output ("local HEAD=" + $head)
git -C $r ls-remote atomgit refs/heads/main 2>&1 | ForEach-Object { Write-Output ("atomgit: " + $_) }
git -C $r -c credential.interactive=false ls-remote origin refs/heads/main 2>&1 | ForEach-Object { Write-Output ("origin: " + $_) }
if ($rcA -ne 0 -or $rcO -ne 0) { Write-Output 'PUSH INCOMPLETE'; exit 1 }
Write-Output '=== CC-HUD DONE ==='
exit 0
