# gemini-pack-classify.ps1 - ASCII only. Masked classification of secret hits. NO raw values printed.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$dir = 'G:\AIrenwu\gemini-pack'
$files = @(Get-ChildItem $dir -Recurse -File -Force)
foreach ($f in $files) {
    $lines = @(Get-Content $f.FullName -ErrorAction SilentlyContinue)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        foreach ($m in [regex]::Matches($line, '(github_pat_|glpat-|gho_|ghp_|sk-)[A-Za-z0-9_\-]+')) {
            $v = $m.Value
            $ph = ($v -match '(?i)(xxx|example|your|redact|placeholder|token|abcdef|11aaaa|<|>|\*)')
            $real = ($v.Length -ge 20) -and (-not $ph)
            Write-Output ($f.Name + ':' + ($i + 1) + ' TOKEN len=' + $v.Length + ' placeholder=' + $ph + ' looks_real=' + $real)
        }
        foreach ($m in [regex]::Matches($line, '(?i)(password|passwd|pwd)\s*[:=]\s*(\S+)')) {
            $v = $m.Groups[2].Value
            $demo = ($v -match '(?i)(123456|password|admin|example|test|changeme|secret|zs|123|hash|qt-u3|\$2)')
            Write-Output ($f.Name + ':' + ($i + 1) + ' PASS len=' + $v.Length + ' demo_or_hash=' + $demo)
        }
    }
}
Write-Output 'CLASSIFY DONE'
