$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$fix = 'G:\AIrenwu\02_项目代码\preview-fixture'
$svgDir = Join-Path $fix 'svg_output'
New-Item -ItemType Directory -Force -Path $svgDir | Out-Null
$svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="1280" height="720" fill="#ffffff"/><text x="100" y="100" font-size="48">preview fixture</text></svg>'
Set-Content -Path (Join-Path $svgDir 'slide_01.svg') -Value $svg -Encoding ASCII
$server = 'D:\QoderToolkit\ppt-master\scripts\svg_editor\server.py'
$py = 'D:\PyCharm\Python\python.exe'
$log = Join-Path $PSScriptRoot 'preview-fixture.log'
$errlog = Join-Path $PSScriptRoot 'preview-fixture.err.log'
$proc = Start-Process -FilePath $py -ArgumentList @($server, $fix, '--no-browser', '--port', '8765') -RedirectStandardOutput $log -RedirectStandardError $errlog -PassThru -NoNewWindow
Start-Sleep -Seconds 5
try {
  $req = [System.Net.HttpWebRequest]::Create('http://127.0.0.1:8765/')
  $req.Proxy = $null
  $req.Timeout = 10000
  $resp = $req.GetResponse()
  Write-Output ('HTTP status=' + [int]$resp.StatusCode)
  $resp.Close()
} catch { Write-Output ('HTTP probe failed: ' + $_.Exception.Message) }
Write-Output ('server alive=' + (-not $proc.HasExited))
if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
Start-Sleep -Seconds 1
$lock = Join-Path $fix 'live_preview\lock.json'
if (Test-Path $lock) { Remove-Item $lock -Force; Write-Output 'stale lock removed' } else { Write-Output 'no stale lock' }
Write-Output '--- stdout tail ---'
if (Test-Path $log) { Get-Content $log -Tail 12 -Encoding UTF8 }
Write-Output '--- stderr tail ---'
if (Test-Path $errlog) { Get-Content $errlog -Tail 12 -Encoding UTF8 }
Write-Output '=== DONE ==='
