$ErrorActionPreference = 'Continue'
$log = Join-Path $PSScriptRoot 'admin-fix-result.log'
if (Test-Path $log) { Remove-Item $log -Force }
$worker = Join-Path $PSScriptRoot 'admin-fix-worker.ps1'
Write-Output 'Requesting elevation (UAC prompt will appear)...'
try {
  Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$worker) -Verb RunAs -ErrorAction Stop
  Write-Output 'elevation requested; waiting for result log (click Yes on UAC)'
} catch {
  Write-Output ('ELEVATION FAILED: ' + $_.Exception.Message)
  exit 1
}
$waited = 0
$max = 150
while (-not (Test-Path $log) -and $waited -lt $max) {
  Start-Sleep -Seconds 3
  $waited += 3
}
if (Test-Path $log) {
  Write-Output ('result log appeared after ~' + $waited + 's')
  Write-Output '--- RESULT ---'
  Get-Content $log -Encoding UTF8
} else {
  Write-Output ('TIMEOUT: no result log after ' + $max + 's (UAC not clicked or worker failed)')
}
