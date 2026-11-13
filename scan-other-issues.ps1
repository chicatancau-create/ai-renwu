# scan-other-issues.ps1 - read-only health scan after the proxy fix. No push, no commit, no credential mutation.
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
function Section([string]$t) { Write-Output ''; Write-Output ('===== ' + $t + ' =====') }

Section 'git GitHub proxy value now'
git config --global --get http.https://github.com.proxy

Section 'end-to-end: git ls-remote GitHub PRIVATE repo via gh helper (fetch only, no prompts)'
$env:GIT_TERMINAL_PROMPT = '0'
git -c credential.interactive=false ls-remote https://github.com/chicatancau-create/fullstack-code.git 2>&1
Write-Output ('rc=' + $LASTEXITCODE)

Section 'E:\fullstack-code health'
git -C E:\fullstack-code status -sb 2>&1
git -C E:\fullstack-code branch -vv 2>&1
git -C E:\fullstack-code log -1 --format='%h %ad %s' --date=short 2>&1
git -C E:\fullstack-code remote -v 2>&1

Section 'atomgit remote ls-remote (fetch only)'
git -c credential.interactive=false ls-remote https://gitcode.com/zhoumoyukuai/fullstack-code.git 2>&1
Write-Output ('rc=' + $LASTEXITCODE)

Section 'who listens on 7890 / 7897 (NO -State Listen filter, per handbook record)'
foreach ($port in 7890, 7897) {
  $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
  if ($conns) {
    $conns | Select-Object LocalAddress, LocalPort, State, OwningProcess -Unique | Format-Table -AutoSize | Out-String
    $conns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
      $p = Get-Process -Id $_ -ErrorAction SilentlyContinue
      if ($p) { Write-Output ('pid ' + $_ + ' = ' + $p.Name + ' | ' + $p.Path) }
    }
  } else { Write-Output ('port ' + $port + ': no connections seen') }
}

Section 'git lfs installed?'
git lfs version 2>&1

Section 'other repos depth1 on E:\ and G:\'
foreach ($root in 'E:\', 'G:\') {
  Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    if (Test-Path (Join-Path $_.FullName '.git')) {
      Write-Output ('--- ' + $_.FullName)
      git -C $_.FullName remote -v 2>&1
      git -C $_.FullName status -sb 2>&1 | Select-Object -First 1
    }
  }
}
Section 'DONE'
