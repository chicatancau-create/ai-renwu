$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$proj = Get-ChildItem 'G:\AIrenwu' -Directory | Where-Object { $_.Name -like '2026-11-04_*' } | Select-Object -First 1
if (-not $proj) { Write-Output 'ABORT: project dir not found'; exit 1 }
Write-Output ('project: ' + $proj.FullName)
$server = 'D:\QoderToolkit\ppt-master\scripts\svg_editor\server.py'
$py = 'D:\PyCharm\Python\python.exe'
$log = Join-Path $PSScriptRoot 'preview-test.log'
$errlog = Join-Path $PSScriptRoot 'preview-test.err.log'
$proc = Start-Process -FilePath $py -ArgumentList @($server, $proj.FullName, '--no-browser', '--port', '8765') -RedirectStandardOutput $log -RedirectStandardError $errlog -PassThru -NoNewWindow
Start-Sleep -Seconds 5
try {
  $req = [System.Net.HttpWebRequest]::Create('http://127.0.0.1:8765/')
  $req.Proxy = $null
  $req.Timeout = 10000
  $resp = $req.GetResponse()
  Write-Output ('HTTP status=' + [int]$resp.StatusCode + ' server=' + $resp.Server)
  $resp.Close()
} catch { Write-Output ('HTTP probe failed: ' + $_.Exception.Message) }
Write-Output ('server process alive=' + (-not $proc.HasExited))
if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
Start-Sleep -Seconds 1
$lock = Join-Path $proj.FullName 'live_preview\lock.json'
if (Test-Path $lock) {
  Write-Output ('stale lock found: ' + (Get-Content $lock -Raw))
  Remove-Item $lock -Force
  Write-Output 'stale lock removed'
} else { Write-Output 'no stale lock' }
Write-Output '--- stdout tail ---'
if (Test-Path $log) { Get-Content $log -Tail 15 -Encoding UTF8 }
Write-Output '--- stderr tail ---'
if (Test-Path $errlog) { Get-Content $errlog -Tail 15 -Encoding UTF8 }
Write-Output '=== DONE ==='
