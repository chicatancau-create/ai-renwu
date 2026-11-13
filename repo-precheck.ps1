# repo-precheck.ps1 - ASCII only. Inventory non-task dirs + secret-pattern scan of root files.
# Prints file:line:pattern only, NEVER matched values (handbook rule: no secret echo).
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$root = 'G:\AIrenwu'

Write-Output '=== SECTION 1: non-task dirs inventory ==='
$skip = @('.memsearch', '.workbuddy', '.workbuddy-ai', '.agent-teams')
$dirs = Get-ChildItem $root -Directory -Force | Where-Object { $_.Name -notlike '2026-*' -and $_.Name -notlike 'DeskBox-*' -and $skip -notcontains $_.Name }
foreach ($d in $dirs) {
    $files = @(Get-ChildItem $d.FullName -Recurse -File -Force -ErrorAction SilentlyContinue)
    $count = $files.Count
    $size = ($files | Measure-Object -Property Length -Sum).Sum
    $hasGit = Test-Path (Join-Path $d.FullName '.git')
    Write-Output ('DIR: ' + $d.Name + ' | files=' + $count + ' | bytes=' + $size + ' | dotgit=' + $hasGit)
    Get-ChildItem $d.FullName -Force | Select-Object -First 12 | ForEach-Object { Write-Output ('   ' + $_.Name) }
}

Write-Output ''
Write-Output '=== SECTION 2: root file secret-pattern scan (names only, no values) ==='
$patterns = @(
    'gho_',
    'github_pat_',
    'glpat-',
    'xoxb-',
    'sk-[A-Za-z0-9]{8}',
    'BEGIN [A-Z ]*PRIVATE KEY',
    'Bearer [A-Za-z0-9_\-\.]{10}',
    '(?i)(password|passwd|pwd)\s*[:=]\s*\S',
    '(?i)(token|secret|api[_-]?key)\s*[:=]\s*[A-Za-z0-9_\-\.]{8}'
)
$rootFiles = @(Get-ChildItem $root -File -Force)
foreach ($f in $rootFiles) {
    $lines = @(Get-Content $f.FullName -ErrorAction SilentlyContinue)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        foreach ($p in $patterns) {
            if ($lines[$i] -match $p) {
                Write-Output ('HIT: ' + $f.Name + ':' + ($i + 1) + ' pattern=' + $p)
            }
        }
    }
}
Write-Output ('ROOT FILES SCANNED: ' + $rootFiles.Count)
Write-Output 'SCAN DONE'
