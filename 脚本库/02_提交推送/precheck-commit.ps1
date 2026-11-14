$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:GIT_TERMINAL_PROMPT = '0'

$repos = @('E:\fullstack-code','G:\cc-hud','G:\CodeWeave')
foreach ($r in $repos) {
  Write-Output ("===== " + $r + " =====")
  Write-Output ("branch=" + (git -C $r branch --show-current))
  git -C $r remote -v | ForEach-Object { "$_" }
  Write-Output '--- status --porcelain (fresh)'
  git -C $r -c core.quotepath=false status --porcelain | ForEach-Object { "$_" }
  Write-Output '--- last 2 commits'
  git -C $r log --oneline -2 | ForEach-Object { "$_" }
  Write-Output ''
}

Write-Output '===== git processes running right now? ====='
Get-Process -Name git -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ("  pid=" + $_.Id) }
Write-Output '(empty means none)'

Write-Output ''
Write-Output '===== CodeWeave freshest working-file mtime (parallel-session check) ====='
$cw = 'G:\CodeWeave'
$files = git -C $cw -c core.quotepath=false ls-files -m -o --exclude-standard
$newest = $null; $newestPath = ''
foreach ($f in $files) {
  $it = Get-Item -LiteralPath (Join-Path $cw $f) -ErrorAction SilentlyContinue
  if ($it -and ($null -eq $newest -or $it.LastWriteTime -gt $newest)) { $newest = $it.LastWriteTime; $newestPath = $f }
}
Write-Output ("now=" + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
if ($newest) { Write-Output ("newest=" + $newest.ToString('yyyy-MM-dd HH:mm:ss') + " file=" + $newestPath) }

Write-Output ''
Write-Output '===== wofule nested .gitignore content ====='
$p = 'E:\fullstack-code'
$gi = git -C $p -c core.quotepath=false ls-files | Where-Object { "$_" -match 'wofule/\.gitignore$' } | Select-Object -First 1
if ($gi) { Write-Output ("path=" + $gi); Get-Content -LiteralPath (Join-Path $p $gi) -Encoding UTF8 }

Write-Output ''
Write-Output '===== uploads / mkdir usage in Web/node js files ====='
Select-String -Path 'E:\fullstack-code\Web\node\*.js' -Pattern 'uploads|mkdir' -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ($_.Filename + ':' + $_.LineNumber + ': ' + $_.Line.Trim()) }

Write-Output ''
Write-Output '===== DONE ====='
