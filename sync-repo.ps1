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
  # Clear session proxy env too: a stale HTTPS_PROXY can outlive the config override.
  # lowSpeed* bounds a stalled push so it cannot hang for minutes.
  $env:HTTP_PROXY = ''; $env:HTTPS_PROXY = ''; $env:ALL_PROXY = ''
  git -c http.https://github.com.proxy= -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=60 push origin main
  Write-Output ('push origin direct rc=' + $LASTEXITCODE)
}

# Verification is delegated to verify-remote-heads.ps1 (single source of truth):
# bounded reads, 3 retries, direct-egress fallback, 40-hex SHA validation, an
# api.github.com cross-check, and three distinct verdicts (VERIFIED / UNVERIFIED /
# real MISMATCH) with exit codes 0 / 2 / 1. An unbounded or unreadable read must
# never decide the verdict: on 2026-11-13 a 300s stall produced a FALSE mismatch
# while both pushes had actually landed.
& powershell -NoProfile -ExecutionPolicy Bypass -File 'G:\AIrenwu\verify-remote-heads.ps1'
exit $LASTEXITCODE
