# git-accounts-check.ps1 - READ-ONLY inspection of git identities on this machine.
# No credential fill, no push, no dry-run (handbook: those can pop GUI / eat stored credentials).
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

function Section([string]$t) { Write-Output ''; Write-Output ('===== ' + $t + ' =====') }

Section 'git version'
git --version

Section 'global git config (show-origin)'
git config --global --list --show-origin 2>&1

Section 'raw global .gitconfig (to see includeIf even if inactive)'
$gc = Join-Path $env:USERPROFILE '.gitconfig'
if (Test-Path $gc) { Get-Content $gc -Encoding UTF8 } else { Write-Output 'no ~/.gitconfig' }

Section 'system git config (show-origin)'
git config --system --list --show-origin 2>&1

Section 'ssh dir listing (names only, never private keys)'
$sshDir = Join-Path $env:USERPROFILE '.ssh'
Write-Output ('ssh dir: ' + $sshDir)
if (Test-Path $sshDir) {
  Get-ChildItem $sshDir -Force | ForEach-Object { Write-Output ($_.Name + '  ' + $_.Length + ' bytes  ' + $_.LastWriteTime) }
} else { Write-Output 'no .ssh directory' }

Section 'ssh config'
$sshCfg = Join-Path $sshDir 'config'
if (Test-Path $sshCfg) { Get-Content $sshCfg -Encoding UTF8 } else { Write-Output 'no ssh config file' }

Section 'public key comments + fingerprints (public material only)'
if (Test-Path $sshDir) {
  Get-ChildItem $sshDir -Filter '*.pub' | ForEach-Object {
    Write-Output ('--- ' + $_.Name)
    $line = (Get-Content $_.FullName -Encoding UTF8 | Select-Object -First 1)
    $parts = $line -split ' '
    if ($parts.Count -ge 3) { Write-Output ('type=' + $parts[0] + ' comment=' + ($parts[2..($parts.Count-1)] -join ' ')) }
    ssh-keygen -lf $_.FullName 2>&1
  }
}

Section 'credential manager git-related entries (targets + users, no secrets)'
cmdkey /list | Select-String -Pattern 'git|github|gitee|gitlab|gitcode|atomgit|bitbucket|coding' -Context 0,3

Section 'gh auth status (token is masked by gh itself)'
gh auth status 2>&1

Section 'git credential-manager version + github account list'
git credential-manager --version 2>&1
git credential-manager github list 2>&1

Section 'workspace root repo check (G:\AIrenwu)'
if (Test-Path 'G:\AIrenwu\.git') {
  git -C 'G:\AIrenwu' config --local --list 2>&1 | Select-String -Pattern 'user\.|remote\.|credential'
} else { Write-Output 'G:\AIrenwu itself is not a git repo' }

Section 'workspace subrepos (depth 1)'
Get-ChildItem 'G:\AIrenwu' -Directory -ErrorAction SilentlyContinue | ForEach-Object {
  $g = Join-Path $_.FullName '.git'
  if (Test-Path $g) {
    Write-Output ('--- ' + $_.FullName)
    git -C $_.FullName config --local --list 2>&1 | Select-String -Pattern 'user\.|remote\.|credential'
  }
}

Section 'known repo E:\fullstack-code (from handbook)'
if (Test-Path 'E:\fullstack-code\.git') {
  git -C 'E:\fullstack-code' config --local --list 2>&1 | Select-String -Pattern 'user\.|remote\.|credential'
} else { Write-Output 'E:\fullstack-code not present' }

Section 'DONE'
