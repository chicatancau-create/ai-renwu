# init-and-push.ps1 - ASCII only. Init repo at G:\AIrenwu, commit whitelisted scripts, dual-push.
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repo = 'G:\AIrenwu'
Set-Location $repo
$env:GIT_TERMINAL_PROMPT = '0'

# guard: no other git process (avoid concurrent index writes)
$gp = @(Get-Process git -ErrorAction SilentlyContinue)
if ($gp.Count -gt 0) { Write-Output ('ABORT: git processes running: ' + $gp.Count); exit 1 }

Write-Output '=== git init ==='
git init -b main 2>&1 | ForEach-Object { "$_" }
git config core.quotepath false

Write-Output '=== stage ==='
git add -A 2>&1 | ForEach-Object { "$_" }
$staged = @(git diff --cached --name-only)
Write-Output ('staged count = ' + $staged.Count)

# privacy guard: abort if any forbidden path staged
$bad = @($staged | Where-Object { $_ -match '(\.memsearch|\.workbuddy|\.agent-teams|^2026-|DeskBox|workbuddy-backup|gemini-pack/0[012]-)' })
if ($bad.Count -gt 0) {
    Write-Output 'ABORT: forbidden path staged:'
    $bad | ForEach-Object { Write-Output $_ }
    git reset 2>&1 | Out-Null
    exit 1
}

# size guard
$bytes = 0
foreach ($p in $staged) { $fp = Join-Path $repo $p; if (Test-Path $fp) { $bytes += (Get-Item $fp).Length } }
Write-Output ('staged bytes = ' + $bytes)
if ($bytes -gt 5MB) { Write-Output 'ABORT: staged too large'; git reset 2>&1 | Out-Null; exit 1 }

Write-Output '=== commit ==='
git commit -F (Join-Path $repo 'msg-repo.txt') 2>&1 | ForEach-Object { "$_" }
Write-Output ('commit rc=' + $LASTEXITCODE)
git --no-pager log --oneline -1 2>&1 | ForEach-Object { "$_" }

Write-Output '=== remotes ==='
git remote add origin https://github.com/chicatancau-create/ai-renwu.git 2>&1 | ForEach-Object { "$_" }
git remote add gitcode https://gitcode.com/zhoumoyukuai/ai-renwu.git 2>&1 | ForEach-Object { "$_" }
git remote -v 2>&1 | ForEach-Object { "$_" }

Write-Output '=== pre-check ls-remote (pure fetch, never rejects credential) ==='
git -c credential.interactive=false ls-remote gitcode 2>&1 | ForEach-Object { "$_" }
$gcPre = $LASTEXITCODE
Write-Output ('gitcode ls-remote rc=' + $gcPre)
git -c credential.interactive=false ls-remote origin 2>&1 | ForEach-Object { "$_" }
$ghPre = $LASTEXITCODE
Write-Output ('origin ls-remote rc=' + $ghPre)
if ($gcPre -ne 0 -or $ghPre -ne 0) { Write-Output 'ABORT: pre-check failed, not pushing (protect credentials)'; exit 1 }

Write-Output '=== push gitcode (direct) ==='
git -c credential.interactive=false push gitcode main 2>&1 | ForEach-Object { "$_" }
Write-Output ('gitcode push rc=' + $LASTEXITCODE)

Write-Output '=== push origin (github via 7890 exit) ==='
git -c credential.interactive=false push origin main 2>&1 | ForEach-Object { "$_" }
Write-Output ('origin push rc=' + $LASTEXITCODE)

Write-Output '=== verify ls-remote ==='
$localHead = (git rev-parse HEAD).Trim()
Write-Output ('local HEAD = ' + $localHead)
$gc = (git ls-remote gitcode refs/heads/main 2>&1) -join ' '
Write-Output ('gitcode main = ' + $gc)
$gh = (git ls-remote origin refs/heads/main 2>&1) -join ' '
Write-Output ('origin main = ' + $gh)
Write-Output 'INIT AND PUSH DONE'
