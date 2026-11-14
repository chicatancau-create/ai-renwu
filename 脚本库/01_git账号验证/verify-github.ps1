# verify-github.ps1 - live GitHub token check via gh CLI. Read-only, no credential mutation.
# 2026-11-13 FIXED (this script was previously broken in three documented ways):
#   1) proxy port 7897 -> 7890. 7897 was the old Clash Verge port; nothing listens
#      there now. Current proxy is FlClash on 127.0.0.1:7890, matching git global
#      http.https://github.com.proxy. 7890 is the LOCAL EGRESS, not a URL rewrite:
#      gh still talks to api.github.com.
#   2) jq args must be QUOTE-FREE. PS 5.1 splits native args on embedded double
#      quotes, so --jq '.login + " id=" + ...' made gh die with
#      "accepts 1 arg(s), received 2". Use plain paths such as --jq .login.
#   3) probes pass -X GET explicitly. gh api switches to POST when -f/-F is present,
#      which once produced a 404 that looked like "the repo was deleted".
# ASCII-only. Run: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\01_git账号验证\verify-github.ps1
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
function Section([string]$t) { Write-Output ''; Write-Output ('===== ' + $t + ' =====') }

Section 'language mode'
Write-Output $ExecutionContext.SessionState.LanguageMode

Section 'proxy 127.0.0.1:7890 real TCP handshake'
$tn = Test-NetConnection -ComputerName 127.0.0.1 -Port 7890 -WarningAction SilentlyContinue
Write-Output ('TcpTestSucceeded=' + $tn.TcpTestSucceeded)

Section 'GitHub live token check: gh api user (direct first)'
$out = gh api user -X GET --jq .login 2>&1
$rc = $LASTEXITCODE
Write-Output ('rc=' + $rc)
Write-Output ($out -join "`n")
if ($rc -ne 0) {
  Write-Output '--- direct failed, retry with HTTPS_PROXY=http://127.0.0.1:7890'
  $env:HTTPS_PROXY = 'http://127.0.0.1:7890'
  $env:HTTP_PROXY = 'http://127.0.0.1:7890'
  $out = gh api user -X GET --jq .login 2>&1
  Write-Output ('rc=' + $LASTEXITCODE)
  Write-Output ($out -join "`n")
}

Section 'GitHub commit attribution: fullstack-code latest commit'
gh api 'repos/chicatancau-create/fullstack-code/commits?per_page=1' -X GET --jq '.[0].commit.author.email' 2>&1
gh api 'repos/chicatancau-create/fullstack-code/commits?per_page=1' -X GET --jq '.[0].author.login' 2>&1

Section 'known_hosts host fields (hosts only)'
$kh = Join-Path $env:USERPROFILE '.ssh\known_hosts'
if (Test-Path $kh) {
  Get-Content $kh -Encoding UTF8 | ForEach-Object { ($_ -split ' ')[0] } | Sort-Object -Unique
}
Section 'DONE'
