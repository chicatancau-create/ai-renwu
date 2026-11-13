# gemini-pack-passcontext.ps1 - ASCII only. Print password-hit lines with values MASKED.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$dir = 'G:\AIrenwu\gemini-pack'
$files = @(Get-ChildItem $dir -Recurse -File -Force -Filter *.md)
foreach ($f in $files) {
    $lines = @(Get-Content $f.FullName -Encoding UTF8 -ErrorAction SilentlyContinue)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match '(?i)(password|passwd|pwd)\s*[:=]\s*\S') {
            $masked = [regex]::Replace($line, '(?i)((password|passwd|pwd)\s*[:=]\s*)(\S+)', '$1[MASKED]')
            $show = $masked.Substring(0, [Math]::Min(280, $masked.Length))
            Write-Output ($f.Name + ':' + ($i + 1) + ' | ' + $show)
        }
    }
}
Write-Output 'MASKED CONTEXT DONE'
