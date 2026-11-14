# run-clash-cleanup.ps1 - launcher: UAC-elevate the worker, poll its log, print results.
# ASCII-only. Run: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\07_机器修复与clash清理\run-clash-cleanup.ps1
$log = Join-Path $PSScriptRoot 'clash-cleanup-result.log'
if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log -Force }
Write-Output 'Launching elevated worker - CLICK YES on the UAC prompt...'
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'clash-cleanup-worker.ps1') -Verb RunAs
$deadline = (Get-Date).AddSeconds(150)
$finished = $false
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if (Test-Path -LiteralPath $log) {
    try {
      $c = Get-Content -LiteralPath $log -Raw -Encoding UTF8
      if ($c -match 'DONE' -or $c -match 'FATAL') { $finished = $true; break }
    } catch { }
  }
}
if (Test-Path -LiteralPath $log) {
  Get-Content -LiteralPath $log -Encoding UTF8 | ForEach-Object { Write-Output $_ }
  if (-not $finished) { Write-Output 'NOTE: deadline reached before DONE/FATAL - log above may be partial' }
} else {
  Write-Output 'NO LOG after 150s - UAC declined or worker failed to start'
}
