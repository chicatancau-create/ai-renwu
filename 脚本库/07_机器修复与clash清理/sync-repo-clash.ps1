# sync-repo-clash.ps1 - commit cleanup-round changes and dual-push.
# Push targets come from git remote config (real URLs): gitcode -> gitcode.com/zhoumoyukuai/ai-renwu.git
# (direct), origin -> github.com/chicatancau-create/ai-renwu.git (via local 7890 exit, not URL substitution).
# ASCII-only. Run: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\07_机器修复与clash清理\sync-repo-clash.ps1
Set-Location G:\AIrenwu
git add -A
$staged = @(git diff --cached --name-only)
Write-Output ("staged count = " + $staged.Count)
if ($staged.Count -eq 0) { Write-Output 'NOTHING STAGED - abort'; exit 1 }
$bad = @($staged | Where-Object { $_ -match '^\.memsearch|^\.workbuddy|^\.agent-teams|^2026-|\.log$' })
if ($bad.Count -gt 0) { Write-Output 'ABORT forbidden paths staged:'; $bad | ForEach-Object { Write-Output $_ }; exit 1 }
foreach ($s in $staged) { Write-Output ("S " + $s) }
$bytes = 0
foreach ($s in $staged) { $p = Join-Path 'G:\AIrenwu' $s; if (Test-Path -LiteralPath $p) { $bytes += (Get-Item -LiteralPath $p).Length } }
Write-Output ("staged bytes = " + $bytes)
if ($bytes -gt 5MB) { Write-Output 'ABORT size cap 5MB'; exit 1 }
git commit -F (Join-Path $PSScriptRoot 'msg-clash-cleanup.txt')
Write-Output ("commit rc=" + $LASTEXITCODE)
if ($LASTEXITCODE -ne 0) { Write-Output 'COMMIT FAILED - abort'; exit 1 }
git push gitcode main
Write-Output ("gitcode push rc=" + $LASTEXITCODE)
git push origin main
Write-Output ("origin push rc=" + $LASTEXITCODE)
$h = git rev-parse HEAD
$g = git ls-remote gitcode refs/heads/main
$o = git ls-remote origin refs/heads/main
Write-Output ("local   = " + $h)
Write-Output ("gitcode = " + $g)
Write-Output ("origin  = " + $o)
if (($g -match $h) -and ($o -match $h)) { Write-Output 'SYNC VERIFIED: both remotes = local HEAD' } else { Write-Output 'SYNC MISMATCH - inspect'; exit 1 }
