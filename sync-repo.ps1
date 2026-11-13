# sync-repo.ps1 - generic incremental commit + dual-push for G:\AIrenwu, with guardrails.
# Guardrails: nothing staged -> abort; private/runtime paths staged -> abort; >5MB -> abort.
# Remotes are taken from the repo's real git config (gitcode direct, origin via the
# machine's 7890 egress from git global http.https://github.com.proxy). No URL rewriting.
# ASCII-only. Run:
#   powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\sync-repo.ps1 -MsgFile G:\AIrenwu\msg-xxx.txt
param([string]$MsgFile = 'G:\AIrenwu\msg-repo-update.txt')
$ErrorActionPreference = 'Continue'
Set-Location 'G:\AIrenwu'
if (-not (Test-Path -LiteralPath $MsgFile)) { Write-Output ('ABORT: msg file missing: ' + $MsgFile); exit 1 }

git add -A
$staged = @(git diff --cached --name-only)
if ($staged.Count -eq 0) { Write-Output 'ABORT: nothing staged'; exit 1 }
Write-Output ('staged: ' + $staged.Count + ' files')

$forbidden = '^\.memsearch|^\.workbuddy|^\.agent-teams|^2026-|\.log$'
$sum = 0
foreach ($f in $staged) {
  if ($f -match $forbidden) { Write-Output ('ABORT: forbidden path staged: ' + $f); exit 1 }
  $it = Get-Item -LiteralPath (Join-Path 'G:\AIrenwu' $f) -ErrorAction SilentlyContinue
  if ($it) { $sum += $it.Length }
  Write-Output ('  ' + $f)
}
Write-Output ('staged bytes: ' + $sum)
if ($sum -gt 5242880) { Write-Output 'ABORT: staged size > 5MB'; exit 1 }

git commit -F $MsgFile
Write-Output ('commit rc=' + $LASTEXITCODE)
git push gitcode main
Write-Output ('push gitcode rc=' + $LASTEXITCODE)
# origin (GitHub) egress fallback, added 2026-11-13 after a real failure:
# the configured 7890 proxy ACCEPTED TCP (Test-NetConnection True, listener present
# with a BLANK State column) yet every GitHub request through it died with
# EOF / TLS 0A000126, while the DIRECT egress worked. Port open != line usable.
# On failure, retry with a PER-COMMAND proxy override. This changes only the local
# egress selection: the global git config is NOT touched and NO URL is substituted
# (origin stays the real github.com address taken from git remote).
git push origin main
$prc = $LASTEXITCODE
Write-Output ('push origin rc=' + $prc)
if ($prc -ne 0) {
  Write-Output '--- origin via configured egress failed; retry DIRECT (per-command override, global config untouched) ---'
  git -c http.https://github.com.proxy= push origin main
  Write-Output ('push origin direct rc=' + $LASTEXITCODE)
}

$local = (git rev-parse HEAD).Trim()
$g = ((git ls-remote gitcode refs/heads/main) -split '\s+')[0]
# Same fallback for verification: an unreadable remote must not be reported as a
# mismatch (handbook rule: "cannot read" is not a negative conclusion).
$o = ((git ls-remote origin refs/heads/main) -split '\s+')[0]
if (-not $o) { $o = ((git -c http.https://github.com.proxy= ls-remote origin refs/heads/main) -split '\s+')[0] }
Write-Output ('local   = ' + $local)
Write-Output ('gitcode = ' + $g)
Write-Output ('origin  = ' + $o)
if ($local -eq $g -and $local -eq $o) { Write-Output 'SYNC VERIFIED' } else { Write-Output 'SYNC MISMATCH' }
