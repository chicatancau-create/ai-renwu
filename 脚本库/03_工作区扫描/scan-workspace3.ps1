$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$p = 'E:\fullstack-code'
$cw = 'G:\CodeWeave'

Write-Output '===== A. foodlist.vue diff (path taken from git, no CJK literals) ====='
$mods = git -C $p -c core.quotepath=false ls-files -m
$vue = $mods | Where-Object { "$_" -match 'foodlist\.vue$' } | Select-Object -First 1
Write-Output ("path=" + $vue)
git -C $p -c core.quotepath=false diff -- $vue 2>&1 | ForEach-Object { "$_" }

Write-Output ''
Write-Output '===== B. wofule project root listing (package.json? manifest?) ====='
$parts = $vue.Split('/')
$wroot = $parts[0] + '/' + $parts[1]
Get-ChildItem -LiteralPath (Join-Path $p $wroot) -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ("  " + $_.Name) }

Write-Output ''
Write-Output '===== C. CodeWeave small diffs ====='
$mods2 = git -C $cw -c core.quotepath=false ls-files -m
foreach ($f in $mods2) {
  if ("$f" -match 'code-editor\.tsx$|code-editor\.test\.tsx$|sha256\.json$|native/README\.md$') {
    Write-Output ("--- diff " + $f)
    git -C $cw -c core.quotepath=false diff -- $f 2>&1 | ForEach-Object { "$_" }
  }
}

Write-Output ''
Write-Output '===== D. CodeWeave evidence dirs: what git would ACTUALLY add (ignore rules applied) ====='
$unt = git -C $cw -c core.quotepath=false ls-files -o --exclude-standard
$ev = $unt | Where-Object { "$_" -match '20261112' }
$total = 0; $n = 0
$byExt = @{}
foreach ($f in $ev) {
  $it = Get-Item -LiteralPath (Join-Path $cw $f) -ErrorAction SilentlyContinue
  if ($it) {
    $n++; $total += $it.Length
    $e = $it.Extension.ToLower()
    if (-not $byExt.ContainsKey($e)) { $byExt[$e] = @(0,0) }
    $byExt[$e][0]++; $byExt[$e][1] += $it.Length
    if ($it.Length -gt 1MB) { Write-Output ("BIGFILE " + $f + " " + [math]::Round($it.Length/1MB,2) + "MB") }
  }
}
Write-Output ("addable files=" + $n + " totalMB=" + [math]::Round($total/1MB,2))
foreach ($k in $byExt.Keys) { Write-Output ("  ext " + $k + " count=" + $byExt[$k][0] + " MB=" + [math]::Round($byExt[$k][1]/1MB,2)) }
Write-Output '--- filesystem subdir sizes (app-side evidence, to compare qt-matrix variants)'
$appEv = $ev | Where-Object { "$_" -match 'qt-matrix|split-audit' } | Select-Object -First 1
if ($appEv) {
  $dir = Split-Path (Join-Path $cw $appEv)
  Get-ChildItem -LiteralPath $dir -Directory | ForEach-Object {
    $s = (Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-Output ("  " + $_.Name + " MB=" + [math]::Round($s/1MB,2))
  }
}

Write-Output ''
Write-Output '===== E. password-hit context lines (judge real secret vs field name) ====='
$audit = $ev | Where-Object { "$_" -match 'split-audit\.md$' } | Select-Object -First 1
if ($audit) {
  Write-Output '--- split-audit.md line 39:'
  (Get-Content -LiteralPath (Join-Path $cw $audit) -Encoding UTF8)[38]
}
$cpp = $mods2 | Where-Object { "$_" -match 'ui_main\.cpp$' } | Select-Object -First 1
if ($cpp) {
  Write-Output '--- ui_main.cpp password lines:'
  $lines = Get-Content -LiteralPath (Join-Path $cw $cpp) -Encoding UTF8
  foreach ($i in @(1984,2930,2933,2934,2935,2937,2938,2991,3834)) { Write-Output ("  L" + $i + ": " + $lines[$i-1].Trim()) }
}

Write-Output ''
Write-Output '===== F. CodeWeave new tokenizer files head ====='
$tok = $unt | Where-Object { "$_" -match 'cached-syntax-tokenizer\.ts$' } | Select-Object -First 1
$tokTest = $unt | Where-Object { "$_" -match 'cached-syntax-tokenizer\.test\.ts$' } | Select-Object -First 1
foreach ($f in @($tok, $tokTest)) {
  if ($f) {
    $it = Get-Item -LiteralPath (Join-Path $cw $f)
    Write-Output ("--- " + $f + " (" + $it.Length + " bytes) head:")
    Get-Content -LiteralPath $it.FullName -TotalCount 12 -Encoding UTF8
  }
}

Write-Output ''
Write-Output '===== DONE ====='
