# verify-optimizations.ps1 - prove the 2026-11-13 retirement of unsafe auto-delete.
# Checks: syntax parse, no LIVE Remove-Item in retired paths, v1 generator inert
# (must NOT touch the .cmd), and a read-only clash-inspect run.
# 2026-11-13 v2: the first version matched COMMENT text and reported two false
# failures (the retirement notes themselves quote "Remove-Item"). Code lines only
# are counted now; comment-only mentions are reported separately for transparency.
# ASCII-only. Run: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\07_机器修复与clash清理\verify-optimizations.ps1
$ErrorActionPreference = 'Continue'
$root = $PSScriptRoot
$bad = 0
$targets = @('admin-fix-worker.ps1','fix-machine.ps1','make-admin-cmd.ps1','clash-inspect.ps1','..\04_规则审计\audit-probe7.ps1','..\01_git账号验证\verify-github.ps1')

Write-Output '=== 1. syntax parse check ==='
foreach ($t in $targets) {
  $errs = $null
  $null = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $root $t), [ref]$null, [ref]$errs)
  if ($errs -and $errs.Count -gt 0) {
    $bad++
    Write-Output ('PARSE FAIL ' + $t + ' errors=' + $errs.Count)
    $errs | Select-Object -First 3 | ForEach-Object { Write-Output ('   line ' + $_.Extent.StartLineNumber + ': ' + $_.Message) }
  } else { Write-Output ('PARSE OK   ' + $t) }
}

Write-Output ''
Write-Output '=== 2. no LIVE auto-delete left in retired paths (comments excluded) ==='
foreach ($t in @('admin-fix-worker.ps1','fix-machine.ps1')) {
  $all = @(Select-String -LiteralPath (Join-Path $root $t) -Pattern 'Remove-Item')
  $live = @($all | Where-Object { $_.Line.TrimStart() -notmatch '^#' })
  $cmt = @($all | Where-Object { $_.Line.TrimStart() -match '^#' })
  if ($live.Count -eq 0) {
    Write-Output ('CLEAN      ' + $t + ' (live Remove-Item=0, comment mentions=' + $cmt.Count + ')')
  } else {
    $bad++
    Write-Output ('STILL DELETES ' + $t + ' live count=' + $live.Count)
    $live | ForEach-Object { Write-Output ('   line ' + $_.LineNumber + ': ' + $_.Line.Trim()) }
  }
}
$mk = @(Get-Content -LiteralPath (Join-Path $root 'make-admin-cmd.ps1'))
$exitLine = 0; $rmLine = 0
for ($i = 0; $i -lt $mk.Count; $i++) {
  $isComment = ($mk[$i].TrimStart() -match '^#')
  if ($exitLine -eq 0 -and $mk[$i] -match '^exit 0') { $exitLine = $i + 1 }
  if ($rmLine -eq 0 -and $mk[$i] -match 'Remove-Item' -and -not $isComment) { $rmLine = $i + 1 }
}
if ($exitLine -gt 0 -and ($rmLine -eq 0 -or $exitLine -lt $rmLine)) {
  Write-Output ('GUARDED    make-admin-cmd.ps1 (exit 0 line ' + $exitLine + ' precedes first live Remove-Item line ' + $rmLine + ' = unreachable history)')
} else { $bad++; Write-Output ('GUARD FAIL make-admin-cmd.ps1 (exitLine=' + $exitLine + ' rmLine=' + $rmLine + ')') }

Write-Output ''
Write-Output '=== 3. v1 generator must be inert (hash of .cmd before/after) ==='
$cmd = Join-Path $root 'fix-admin-items.cmd'
$h1 = (Get-FileHash -LiteralPath $cmd -Algorithm SHA256).Hash
$l1 = (Get-Item -LiteralPath $cmd).Length
$out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'make-admin-cmd.ps1') 2>&1
Write-Output ($out -join "`n")
$h2 = (Get-FileHash -LiteralPath $cmd -Algorithm SHA256).Hash
$l2 = (Get-Item -LiteralPath $cmd).Length
if ($h1 -eq $h2 -and $l1 -eq $l2) { Write-Output ('CMD UNCHANGED OK (' + $l2 + ' bytes, sha256 identical)') }
else { $bad++; Write-Output 'CMD CHANGED - RETIREMENT GUARD FAILED' }

Write-Output ''
Write-Output '=== 4. clash-inspect.ps1 (read-only, precise names, Test-Path guarded) ==='
$o = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'clash-inspect.ps1') 2>&1
Write-Output ($o -join "`n")

Write-Output ''
Write-Output '=== 5. repo status ==='
Set-Location $root
git status --porcelain
Write-Output ''
Write-Output ('TOTAL FAILURES: ' + $bad)
Write-Output '=== DONE ==='
