# repo-precheck-dirs.ps1 - ASCII only. Secret-pattern scan of candidate tool dirs.
# Prints file:line:pattern only, NEVER matched values.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$root = 'G:\AIrenwu'
$targets = @('dsh-preset-switcher', 'gemini-pack')
$patterns = @(
    'gho_', 'github_pat_', 'glpat-', 'xoxb-', 'sk-[A-Za-z0-9]{8}',
    'BEGIN [A-Z ]*PRIVATE KEY', 'Bearer [A-Za-z0-9_\-\.]{10}',
    '(?i)(password|passwd|pwd)\s*[:=]\s*\S',
    '(?i)(token|secret|api[_-]?key)\s*[:=]\s*[A-Za-z0-9_\-\.]{8}'
)
foreach ($t in $targets) {
    $dir = Join-Path $root $t
    $files = @(Get-ChildItem $dir -Recurse -File -Force -ErrorAction SilentlyContinue)
    Write-Output ('=== ' + $t + ' (' + $files.Count + ' files) ===')
    foreach ($f in $files) {
        $lines = @(Get-Content $f.FullName -ErrorAction SilentlyContinue)
        for ($i = 0; $i -lt $lines.Count; $i++) {
            foreach ($p in $patterns) {
                if ($lines[$i] -match $p) {
                    Write-Output ('HIT: ' + $f.FullName.Substring($root.Length + 1) + ':' + ($i + 1) + ' pattern=' + $p)
                }
            }
        }
    }
}
Write-Output 'DIR SCAN DONE'
