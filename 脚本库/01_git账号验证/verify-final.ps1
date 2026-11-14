# verify-final.ps1 - last read-only checks: proxy port 7890, GitHub repo list, GitCode repo existence.
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
function Section([string]$t) { Write-Output ''; Write-Output ('===== ' + $t + ' =====') }

Section 'port 7890 listening? (system proxy target)'
$tn = Test-NetConnection -ComputerName 127.0.0.1 -Port 7890 -WarningAction SilentlyContinue
Write-Output ('TcpTestSucceeded=' + $tn.TcpTestSucceeded)

Section 'GitHub account profile'
gh api user --jq '{login,name,public_repos,created_at}' 2>&1

Section 'GitHub repos under this account (names only)'
gh api user/repos -f per_page=100 --jq '.[].full_name' 2>&1

Section 'GitCode repo existence: zhoumoyukuai/fullstack-code (anonymous ls-remote, no prompts)'
$env:GIT_TERMINAL_PROMPT = '0'
git -c credential.interactive=false ls-remote https://gitcode.com/zhoumoyukuai/fullstack-code.git 2>&1
Write-Output ('rc=' + $LASTEXITCODE)
Section 'DONE'
