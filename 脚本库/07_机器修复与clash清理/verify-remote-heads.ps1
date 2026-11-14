# verify-remote-heads.ps1 - read local + both remote HEADs with BOUNDED, RETRIED reads
# and a THREE-STATE verdict. Exit code: 0 verified, 2 unreadable (UNVERIFIED), 1 real mismatch.
#
# Why this exists (2026-11-13, two false verdicts in one round):
#  1) sync-repo.ps1 verified with an unbounded ls-remote. The configured 7890 egress
#     failed, the direct retry STALLED for 300s and returned empty -> the script printed
#     "SYNC MISMATCH" although BOTH pushes had landed (5f6bcbd..f997553 on both remotes).
#  2) The first version of THIS script hit PowerShell function-output pollution:
#     Write-Output diagnostics inside a function are part of its return value, so $o
#     became the "attempt 1..3" text instead of ''. That skipped the direct fallback
#     (-not $o was false) AND made the verdict claim a real mismatch.
#     Fix: diagnostics go to the HOST stream (Write-Host), and only a 40-hex SHA is
#     ever returned. The api.github.com cross-check in that same run proved the push
#     had landed (sha == local HEAD).
# Handbook rule: "cannot read" is NOT a negative conclusion.
#
# URL discipline: remotes come from `git remote` (real gitcode.com / github.com addresses);
# the cross-check goes to api.github.com via gh. Clearing proxy env and the per-command
# http.proxy override only select the LOCAL EGRESS - no address is substituted and the
# global git config is never modified.
$ErrorActionPreference = 'Continue'
Set-Location G:\AIrenwu

# A stale session HTTPS_PROXY can outlive a git config override; clear both.
$env:HTTP_PROXY = ''; $env:HTTPS_PROXY = ''; $env:ALL_PROXY = ''
$env:GIT_TERMINAL_PROMPT = '0'

function Get-RemoteHead([string]$remote, [bool]$direct) {
  for ($i = 1; $i -le 3; $i++) {
    # lowSpeedLimit/lowSpeedTime bound a stalled transfer instead of hanging forever.
    $ga = @('-c', 'credential.interactive=false', '-c', 'http.lowSpeedLimit=1000', '-c', 'http.lowSpeedTime=20')
    if ($direct) { $ga += @('-c', 'http.https://github.com.proxy=') }
    $ga += @('ls-remote', $remote, 'refs/heads/main')
    $out = & git @ga 2>$null
    $rc = $LASTEXITCODE
    if ($rc -eq 0 -and $out) {
      $sha = (($out | Select-Object -First 1) -split '\s+')[0]
      if ($sha -match '^[0-9a-f]{40}$') { return $sha }
    }
    # Write-Host = host/information stream, NOT captured by assignment. Never Write-Output here.
    Write-Host ("  attempt {0}: {1} direct={2} rc={3}" -f $i, $remote, $direct, $rc)
    Start-Sleep -Seconds 3
  }
  return ''
}

$local = (git rev-parse HEAD).Trim()
Write-Output ('local   = ' + $local)

$g = Get-RemoteHead 'gitcode' $false
Write-Output ('gitcode = ' + $g)

$o = Get-RemoteHead 'origin' $false
if (-not $o) {
  Write-Output '--- origin unreadable via configured egress; retry DIRECT (per-command, global config untouched) ---'
  $o = Get-RemoteHead 'origin' $true
}
Write-Output ('origin  = ' + $o)

# Independent cross-check over a different protocol path (HTTPS API, not git transport).
$api = (& gh api 'repos/chicatancau-create/ai-renwu/commits?per_page=1&sha=main' -X GET --jq '.[0].sha' 2>$null)
$arc = $LASTEXITCODE
if ($api) { $api = ([string]$api).Trim() } else { $api = '' }
Write-Output ('origin via api.github.com = ' + $api + ' (rc=' + $arc + ')')

$gOk = ($g -match '^[0-9a-f]{40}$')
$oOk = ($o -match '^[0-9a-f]{40}$')
$aOk = ($api -match '^[0-9a-f]{40}$')

if ($gOk -and $oOk -and $local -eq $g -and $local -eq $o) {
  Write-Output 'SYNC VERIFIED (git transport, both remotes)'
  $code = 0
} elseif ($gOk -and $local -eq $g -and $aOk -and $api -eq $local) {
  Write-Output 'SYNC VERIFIED (gitcode via git transport; origin via api.github.com cross-check - git transport to origin unreadable)'
  $code = 0
} elseif ((-not $gOk) -or ((-not $oOk) -and (-not $aOk))) {
  Write-Output 'UNVERIFIED: a remote could not be read - this is NOT a mismatch'
  $code = 2
} else {
  Write-Output 'SYNC MISMATCH (real: remotes readable and different from local HEAD)'
  $code = 1
}
Write-Output '=== DONE ==='
exit $code
