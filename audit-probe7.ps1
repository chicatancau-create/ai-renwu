$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output '=== 1. WorkBuddy Run key ==='
$run = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
Write-Output ('WorkBuddy.WorkBuddyAI = ' + $run.'WorkBuddy.WorkBuddyAI')
Write-Output ('target exe exists: ' + (Test-Path 'D:\WorkBuddyAI\WorkBuddy.exe'))

Write-Output '=== 2. flask / pip ==='
& 'D:\PyCharm\Python\python.exe' -c "import flask; print('flask', flask.__version__)" 2>&1 | ForEach-Object { Write-Output $_ }
Write-Output ('import rc=' + $LASTEXITCODE)
& 'D:\PyCharm\Python\python.exe' -m pip --version 2>&1 | ForEach-Object { Write-Output $_ }
& 'D:\PyCharm\Python\python.exe' -m pip config list 2>&1 | ForEach-Object { Write-Output $_ }

Write-Output '=== 3. MSVC / vswhere ==='
$vswhere = ${env:ProgramFiles(x86)} + '\Microsoft Visual Studio\Installer\vswhere.exe'
Write-Output ('vswhere exists: ' + (Test-Path $vswhere))
if (Test-Path $vswhere) {
  $vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  Write-Output ('VS install: ' + $vsPath)
  if ($vsPath) {
    $vcvars = Join-Path $vsPath 'VC\Auxiliary\Build\vcvars64.bat'
    Write-Output ('vcvars64 exists: ' + (Test-Path $vcvars))
  }
}

Write-Output '=== 4. MySQL ==='
Get-Service | Where-Object { $_.Name -like 'MySQL*' -or $_.DisplayName -like '*MySQL*' } | ForEach-Object { Write-Output ($_.Name + ' | ' + $_.Status + ' | ' + $_.StartType) }
$my = Get-Command mysql -ErrorAction SilentlyContinue
if ($my) { Write-Output ('mysql client: ' + $my.Source) } else { Write-Output 'mysql client: NOT FOUND' }
$c3306 = Get-NetTCPConnection -LocalPort 3306 -ErrorAction SilentlyContinue
if ($c3306) { $c3306 | Select-Object -First 3 | ForEach-Object { Write-Output ('3306 ' + $_.LocalAddress + ' pid=' + $_.OwningProcess) } } else { Write-Output '3306 listeners: NONE' }

Write-Output '=== 5. clash-verge-service residual ==='
$cv = 'C:\ProgramData\clash-verge-service'
if (Test-Path $cv) {
  Get-ChildItem $cv -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ($_.FullName + ' | ' + $_.Length + 'B') }
  $svc = Get-Service | Where-Object { $_.Name -like '*clash*' }
  if ($svc) { $svc | ForEach-Object { Write-Output ('clash service: ' + $_.Name + ' ' + $_.Status) } } else { Write-Output 'clash services: NONE' }
  $procs = Get-Process | Where-Object { $_.Path -like '*clash-verge*' }
  if ($procs) { $procs | ForEach-Object { Write-Output ('clash-verge proc: ' + $_.Id) } } else { Write-Output 'clash-verge processes: NONE' }
} else { Write-Output 'dir gone' }

Write-Output '=== 6. Radmin / route baseline ==='
Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Radmin*' -or $_.InterfaceAlias -like '*WLAN*' } | ForEach-Object { Write-Output ($_.InterfaceAlias + ' ifIndex=' + $_.InterfaceIndex + ' metric=' + $_.InterfaceMetric) }
Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ('default route ifIndex=' + $_.ifIndex + ' nextHop=' + $_.NextHop + ' routeMetric=' + $_.RouteMetric) }
$fnr = Find-NetRoute -RemoteIPAddress 8.8.8.8 -ErrorAction SilentlyContinue
if ($fnr) { Write-Output ('Find-NetRoute localIP=' + $fnr[0].IPAddress + ' ifIndex=' + $fnr[0].InterfaceIndex) }

Write-Output '=== 7. ppt-master project / server ==='
Write-Output ('server.py exists: ' + (Test-Path 'D:\QoderToolkit\ppt-master\scripts\svg_editor\server.py'))
Get-ChildItem 'G:\AIrenwu' -Directory | Where-Object { $_.Name -like '2026-11-04*' } | ForEach-Object { Write-Output ('project dir: ' + $_.FullName) }

Write-Output '=== 8. H drive jars ==='
Get-ChildItem 'H:\' -Directory -ErrorAction SilentlyContinue | ForEach-Object {
  $jars = Get-ChildItem $_.FullName -Filter '*.jar' -File -ErrorAction SilentlyContinue
  foreach ($j in $jars) { Write-Output ($j.FullName + ' | ' + $j.Length + 'B') }
}
Write-Output '=== DONE ==='
