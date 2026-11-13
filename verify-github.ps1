# verify-github.ps1 - live GitHub token check via gh CLI. Read-only, no credential mutation.
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
function Section([string]$t) { Write-Output ''; Write-Output ('===== ' + $t + ' =====') }

Section 'language mode'
Write-Output $ExecutionContext.SessionState.LanguageMode

Section 'proxy 127.0.0.1:7897 listening?'
$tn = Test-NetConnection -ComputerName 127.0.0.1 -Port 7897 -WarningAction SilentlyContinue
Write-Output ('TcpTestSucceeded=' + $tn.TcpTestSucceeded)

Section 'GitHub live token check: gh api user (direct first)'
$out = gh api user --jq '.login + " id=" + (.id|tostring)' 2>&1
$rc = $LASTEXITCODE
Write-Output ('rc=' + $rc)
Write-Output ($out -join "`n")
if ($rc -ne 0) {
  Write-Output '--- direct failed, retry with HTTPS_PROXY=http://127.0.0.1:7897'
  $env:HTTPS_PROXY = 'http://127.0.0.1:7897'
  $env:HTTP_PROXY = 'http://127.0.0.1:7897'
  $out = gh api user --jq '.login + " id=" + (.id|tostring)' 2>&1
  Write-Output ('rc=' + $LASTEXITCODE)
  Write-Output ($out -join "`n")
}

Section 'GitHub commit attribution: fullstack-code latest commit'
gh api 'repos/chicatancau-create/fullstack-code/commits?per_page=1' --jq '.[0].commit.author.email + " => GitHub author: " + (.[0].author.login // "null (email not linked to GitHub)")' 2>&1

Section 'known_hosts host fields (hosts only)'
$kh = Join-Path $env:USERPROFILE '.ssh\known_hosts'
if (Test-Path $kh) {
  Get-Content $kh -Encoding UTF8 | ForEach-Object { ($_ -split ' ')[0] } | Sort-Object -Unique
}
Section 'DONE'
