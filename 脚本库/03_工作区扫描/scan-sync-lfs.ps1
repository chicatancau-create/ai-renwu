# scan-sync-lfs.ps1 - read-only: sync state of the other two repos + LFS usage check. No push, no commit.
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$env:GIT_TERMINAL_PROMPT = '0'

foreach ($repo in 'G:\cc-hud', 'G:\CodeWeave') {
  Write-Output ''
  Write-Output ('===== ' + $repo + ' =====')
  $branch = git -C $repo rev-parse --abbrev-ref HEAD 2>&1
  $head = git -C $repo rev-parse HEAD 2>&1
  Write-Output ('local ' + $branch + ' = ' + $head)
  $email = git -C $repo config --local --get user.email 2>&1
  Write-Output ('local user.email = [' + $email + ']')
  foreach ($r in (git -C $repo remote)) {
    Write-Output ('--- ls-remote --heads ' + $r)
    git -C $repo -c credential.interactive=false ls-remote --heads $r 2>&1
    Write-Output ('rc=' + $LASTEXITCODE)
  }
}

Write-Output ''
Write-Output '===== LFS usage: tracked .gitattributes containing filter=lfs ====='
foreach ($repo in 'E:\fullstack-code', 'G:\cc-hud', 'G:\CodeWeave') {
  Write-Output ('--- ' + $repo)
  git -C $repo grep -n 'filter=lfs' -- '*.gitattributes' 2>&1
  Write-Output ('rc=' + $LASTEXITCODE + '  (rc=1 means no match)')
}
Write-Output ''
Write-Output '===== DONE ====='
