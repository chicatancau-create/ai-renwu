$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Inventory-Dir($full, $label) {
  if (Test-Path -LiteralPath $full -PathType Container) {
    $files = Get-ChildItem -LiteralPath $full -Recurse -File -ErrorAction SilentlyContinue
    $count = ($files | Measure-Object).Count
    $size = ($files | Measure-Object -Property Length -Sum).Sum
    Write-Output ("DIR " + $label + " files=" + $count + " totalMB=" + [math]::Round($size/1MB,2))
    if (Test-Path -LiteralPath (Join-Path $full '.git')) { Write-Output '  !! HAS OWN .git (embedded repo)' }
    Get-ChildItem -LiteralPath $full -ErrorAction SilentlyContinue | Select-Object -First 12 | ForEach-Object { Write-Output ("  " + $_.Name) }
    $files | Where-Object { $_.Length -gt 5MB } | Select-Object -First 5 | ForEach-Object { Write-Output ("  BIG " + $_.Name + " " + [math]::Round($_.Length/1MB,2) + "MB") }
  } else {
    Write-Output ("NOT-A-DIR " + $label)
  }
}

Write-Output '===== A. fullstack-code untracked inventory (quotepath off, incl CJK paths) ====='
$p = 'E:\fullstack-code'
$unt = git -C $p -c core.quotepath=false status --porcelain=v1 | Where-Object { "$_" -match '^\?\? ' } | ForEach-Object { ("$_").Substring(3) }
foreach ($u in $unt) {
  $full = Join-Path $p $u
  if (Test-Path -LiteralPath $full -PathType Container) { Inventory-Dir $full $u }
}

Write-Output ''
Write-Output '===== B. uploads content ====='
Get-ChildItem -LiteralPath 'E:\fullstack-code\Web\node\uploads' -Recurse -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ($_.FullName.Replace('E:\fullstack-code\','') + " " + $_.Length) }

Write-Output ''
Write-Output '===== C. harmonyMall README head ====='
Get-Content -LiteralPath 'E:\fullstack-code\Harmony\harmonyMall-master\README.md' -TotalCount 15 -Encoding UTF8

Write-Output ''
Write-Output '===== D. fullstack-code diffs (backup.sql truncated) ====='
git -C $p -c core.quotepath=false diff -- Web/node/async.js Web/node/package-lock.json projects/project02-collab/evidence/fault-drills.json projects/project02-collab/evidence/manifest.json projects/project02-collab/evidence/perf.json projects/project04-saas/evidence/audit_log.txt projects/project04-saas/evidence/multi_tenant.txt projects/project04-saas/evidence/rbac.txt 2>&1 | ForEach-Object { "$_" }
Write-Output '--- foodlist.vue diff'
git -C $p -c core.quotepath=false diff -- '跨平台应用开发/wofule/pages/foodlist/foodlist.vue' 2>&1 | ForEach-Object { "$_" }
Write-Output '--- p02-backup.sql diff (first 50 lines)'
git -C $p -c core.quotepath=false diff -- projects/project02-collab/evidence/p02-backup.sql 2>&1 | Select-Object -First 50 | ForEach-Object { "$_" }

Write-Output ''
Write-Output '===== E. secret-pattern scan (file+pattern+line numbers only, no content) ====='
$patterns = @('password','passwd','api[_-]?key','secret','PRIVATE KEY','ghp_','gho_','sk-[A-Za-z0-9]{10}','Bearer [A-Za-z0-9]','access[_-]?key')
foreach ($repo in @('E:\fullstack-code','G:\CodeWeave')) {
  Write-Output ("--- repo " + $repo)
  $cands = git -C $repo -c core.quotepath=false ls-files -m -o --exclude-standard | Where-Object { "$_" -match '\.(js|ts|tsx|json|json5|sql|txt|md|ets|vue|html|qml|cpp)$' }
  foreach ($f in $cands) {
    $full = Join-Path $repo $f
    foreach ($pat in $patterns) {
      $hits = Select-String -LiteralPath $full -Pattern $pat -ErrorAction SilentlyContinue
      if ($hits) { Write-Output ("HIT " + $f + " pattern=" + $pat + " lines=" + (($hits | ForEach-Object { $_.LineNumber }) -join ',')) }
    }
  }
}

Write-Output ''
Write-Output '===== F. CodeWeave untracked evidence dirs + small diffs ====='
$cw = 'G:\CodeWeave'
$unt2 = git -C $cw -c core.quotepath=false status --porcelain=v1 | Where-Object { "$_" -match '^\?\? ' } | ForEach-Object { ("$_").Substring(3) }
foreach ($u in $unt2) {
  $full = Join-Path $cw $u
  if (Test-Path -LiteralPath $full -PathType Container) {
    Inventory-Dir $full $u
    Get-ChildItem -LiteralPath $full -Recurse -File -Filter *.md -ErrorAction SilentlyContinue | Select-Object -First 2 | ForEach-Object {
      Write-Output ("--- head of " + $_.Name)
      Get-Content -LiteralPath $_.FullName -TotalCount 25 -Encoding UTF8
    }
  }
}
Write-Output '--- code-editor.tsx + sha256.json + native README diffs'
git -C $cw -c core.quotepath=false diff -- '网页端/项目/src/components/code-editor.tsx' '应用端/工程文件/验收证据/Phase41-split-comparison-20261111/sha256.json' '应用端/项目/native/README.md' 2>&1 | ForEach-Object { "$_" }

Write-Output ''
Write-Output '===== G. cc-hud unpushed commit stat ====='
git -C G:\cc-hud show --stat --oneline 9efba67 2>&1 | Select-Object -First 25 | ForEach-Object { "$_" }

Write-Output ''
Write-Output '===== DONE ====='
