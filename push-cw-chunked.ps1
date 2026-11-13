$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$repo = 'G:\CodeWeave'
$branch = 'codex/project-layout-20261106'
$base = '229a411bf7b7b21e4220520a637837d140388867'
$ref = "refs/heads/$branch"

$gp = Get-Process -Name git -ErrorAction SilentlyContinue
if ($gp) { Write-Output 'ABORT: another git process is running'; exit 2 }

$head = (git -C $repo rev-parse HEAD).Trim()
Write-Output ("local HEAD=" + $head)

$commits = @(git -C $repo rev-list --reverse "$base..HEAD")
Write-Output ("commits to push=" + $commits.Count)
if ($commits.Count -eq 0) { Write-Output 'nothing to push'; exit 0 }

function Try-Push([string]$sha, [int]$attempts) {
    for ($a = 1; $a -le $attempts; $a++) {
        Write-Output ("  attempt " + $a + " -> " + $sha.Substring(0, 8) + "  " + (Get-Date -Format 'HH:mm:ss'))
        $out = git -C $repo push origin ($sha + ':' + $ref) 2>&1
        $rc = $LASTEXITCODE
        $out | ForEach-Object { Write-Output ("    " + $_) }
        if ($rc -eq 0) { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}

$i = 0
$size = 10
while ($i -lt $commits.Count) {
    $end = [Math]::Min($i + $size, $commits.Count) - 1
    $target = $commits[$end]
    Write-Output ("chunk [" + $i + ".." + $end + "] count=" + ($end - $i + 1))
    $ok = Try-Push $target 2
    if ($ok) {
        $i = $end + 1
        $size = 10
    }
    else {
        if ($size -gt 1) {
            $size = [Math]::Max(1, [int]($size / 2))
            Write-Output ("  chunk failed, shrink size to " + $size)
        }
        else {
            Write-Output 'FATAL: single-commit push failed after retries'
            exit 1
        }
    }
}

Write-Output '=== verify remote head ==='
$remote = (git -C $repo ls-remote origin $ref)
Write-Output ("origin: " + $remote)
if ($remote -match $head) { Write-Output 'PUSH COMPLETE: origin == local HEAD' }
else { Write-Output 'PUSH INCOMPLETE'; exit 1 }
