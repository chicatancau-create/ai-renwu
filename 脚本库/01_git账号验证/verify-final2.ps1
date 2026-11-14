# verify-final2.ps1 - corrected GET-only probes (gh api -f defaults to POST; must force -X GET).
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
function Section([string]$t) { Write-Output ''; Write-Output ('===== ' + $t + ' =====') }

Section 'GitHub repos under account (explicit GET)'
$repos = gh api user/repos -X GET -f per_page=100 --jq '.[].full_name' 2>&1
$rc = $LASTEXITCODE
Write-Output ('rc=' + $rc)
Write-Output ($repos -join "`n")

Section 'GitHub fullstack-code repo existence (explicit GET)'
gh api repos/chicatancau-create/fullstack-code -X GET --jq '{full_name,private,pushed_at}' 2>&1

if ($rc -eq 0) {
  $target = $null
  foreach ($r in $repos) { if ($r -match 'fullstack-code') { $target = $r; break } }
  if (-not $target -and $repos.Count -gt 0) { $target = $repos[0] }
  if ($target) {
    Section ('latest commit attribution on ' + $target + ' (explicit GET)')
    gh api ('repos/' + $target + '/commits') -X GET -f per_page=1 --jq '.[0].commit.author.email' 2>&1
    gh api ('repos/' + $target + '/commits') -X GET -f per_page=1 --jq '.[0].author.login' 2>&1
  }
}
Section 'DONE'
