# try-direct-github.ps1 - the 7890 egress accepts TCP but GitHub requests die (EOF /
# TLS 0A000126). Test whether the DIRECT egress works, and if so finish the dual-push
# using a PER-COMMAND proxy override. The global git config is NOT modified, and no
# URL is substituted: origin stays https://github.com/chicatancau-create/ai-renwu.git.
# Safety: ls-remote is a pure fetch (never triggers credential reject); no --dry-run.
# ASCII-only. Run: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\07_机器修复与clash清理\try-direct-github.ps1
$ErrorActionPreference = 'Continue'
Set-Location 'G:\AIrenwu'
Remove-Item Env:\HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:\HTTP_PROXY -ErrorAction SilentlyContinue
$env:GIT_TERMINAL_PROMPT = '0'

Write-Output '=== A. minimal real request DIRECT: gh api user (api.github.com, no proxy) ==='
gh api user -X GET --jq .login 2>&1
$ghrc = $LASTEXITCODE
Write-Output ('gh direct rc=' + $ghrc)

Write-Output ''
Write-Output '=== B. ls-remote origin, per-command proxy disabled (pure fetch) ==='
git -c http.https://github.com.proxy= -c credential.interactive=false ls-remote origin refs/heads/main 2>&1
$lsrc = $LASTEXITCODE
Write-Output ('ls-remote direct rc=' + $lsrc)

Write-Output ''
if ($lsrc -eq 0) {
  Write-Output '=== C. direct egress works -> push origin main (per-command override only) ==='
  git -c http.https://github.com.proxy= push origin main 2>&1
  Write-Output ('push origin rc=' + $LASTEXITCODE)
} else {
  Write-Output '=== C. SKIP push: direct egress also unusable (both paths down) ==='
}

Write-Output ''
Write-Output '=== D. verify both remotes against local HEAD ==='
$local = (git rev-parse HEAD).Trim()
$g = ((git ls-remote gitcode refs/heads/main) -split '\s+')[0]
if ($lsrc -eq 0) { $o = ((git -c http.https://github.com.proxy= ls-remote origin refs/heads/main) -split '\s+')[0] }
else { $o = ((git ls-remote origin refs/heads/main) -split '\s+')[0] }
Write-Output ('local   = ' + $local)
Write-Output ('gitcode = ' + $g)
Write-Output ('origin  = ' + $o)
if ($local -eq $g -and $local -eq $o) { Write-Output 'SYNC VERIFIED' } else { Write-Output 'SYNC MISMATCH (GitHub pending)' }

Write-Output ''
Write-Output '=== E. global proxy config must be UNCHANGED ==='
git config --global --get http.https://github.com.proxy
Write-Output '=== DONE ==='
