$ErrorActionPreference = 'Continue'
$repos = @('E:\fullstack-code','G:\cc-hud','G:\CodeWeave')
foreach ($p in $repos) {
  Write-Output ''
  Write-Output ('################ REPO ' + $p)
  Write-Output '--- branch/tracking'
  git -C $p status -sb 2>&1 | Select-Object -First 1 | ForEach-Object { "$_" }
  Write-Output '--- porcelain (full)'
  git -C $p status --porcelain=v1 2>&1 | ForEach-Object { "$_" }
  Write-Output '--- staged diffstat'
  git -C $p diff --cached --stat 2>&1 | ForEach-Object { "$_" }
  Write-Output '--- unstaged diffstat'
  git -C $p diff --stat 2>&1 | ForEach-Object { "$_" }
  Write-Output '--- unpushed commits (local branches not on any remote), first 20'
  git -C $p log --branches --not --remotes --oneline 2>&1 | Select-Object -First 20 | ForEach-Object { "$_" }
  Write-Output '--- .gitignore'
  $gi = Join-Path $p '.gitignore'
  if (Test-Path $gi) { Get-Content $gi | ForEach-Object { "$_" } } else { Write-Output '(no .gitignore)' }
  Write-Output '--- untracked inventory'
  $unt = git -C $p status --porcelain=v1 2>&1 | Where-Object { "$_" -match '^\?\? ' } | ForEach-Object { ("$_").Substring(3) }
  foreach ($u in $unt) {
    $full = Join-Path $p $u
    if (Test-Path $full -PathType Container) {
      $files = Get-ChildItem $full -Recurse -File -ErrorAction SilentlyContinue
      $count = ($files | Measure-Object).Count
      $size = ($files | Measure-Object -Property Length -Sum).Sum
      Write-Output ("DIR " + $u + " files=" + $count + " totalMB=" + [math]::Round($size/1MB,2))
      if (Test-Path (Join-Path $full '.git')) { Write-Output '  !! HAS OWN .git (embedded repo)' }
      Get-ChildItem $full -ErrorAction SilentlyContinue | Select-Object -First 15 | ForEach-Object { Write-Output ("  " + $_.Name) }
      $files | Where-Object { $_.Length -gt 5MB } | Select-Object -First 10 | ForEach-Object { Write-Output ("  BIG " + $_.FullName + " " + [math]::Round($_.Length/1MB,2) + "MB") }
    } else {
      $it = Get-Item $full -ErrorAction SilentlyContinue
      if ($it) { Write-Output ("FILE " + $u + " " + [math]::Round($it.Length/1KB,1) + "KB") }
    }
  }
}
Write-Output ''
Write-Output '################ DONE'
