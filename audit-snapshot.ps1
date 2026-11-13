$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output '=== PS version ==='
$PSVersionTable.PSVersion.ToString()

Write-Output '=== pwsh 7 ==='
$p = Get-Command pwsh -ErrorAction SilentlyContinue
if ($p) { $p.Source } else { 'NOT FOUND' }

Write-Output '=== default route v4 ==='
Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 -ErrorAction SilentlyContinue | ForEach-Object { 'ifIndex=' + $_.ifIndex + ' nextHop=' + $_.NextHop + ' routeMetric=' + $_.RouteMetric + ' ifMetric=' + $_.InterfaceMetric }

Write-Output '=== IPv4 interface metrics (sorted) ==='
Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue | Sort-Object InterfaceMetric | ForEach-Object { 'ifIndex=' + $_.ifIndex + ' metric=' + $_.InterfaceMetric + ' alias=' + $_.InterfaceAlias }

Write-Output '=== adapters ==='
Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object { $_.Name + ' | ' + $_.InterfaceDescription + ' | ' + $_.Status }

Write-Output '=== listeners 7890 / 7897 (no State filter) ==='
$c90 = Get-NetTCPConnection -LocalPort 7890 -ErrorAction SilentlyContinue
if ($c90) { $c90 | Select-Object -First 2 | ForEach-Object { $pr = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; '7890 pid=' + $_.OwningProcess + ' name=' + $pr.ProcessName + ' path=' + $pr.Path } } else { '7890 NONE' }
$c97 = Get-NetTCPConnection -LocalPort 7897 -ErrorAction SilentlyContinue
if ($c97) { $c97 | Select-Object -First 2 | ForEach-Object { '7897 pid=' + $_.OwningProcess } } else { '7897 NONE' }

Write-Output '=== system proxy ==='
$reg = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
'ProxyEnable=' + $reg.ProxyEnable + ' ProxyServer=' + $reg.ProxyServer

Write-Output '=== path checks ==='
$paths = @(
 'C:\Users\Admin\.dsh\tools\gui-control\useridle.py',
 'C:\Users\Admin\.dsh\tools\gui-control\pwcap.py',
 'E:\XD\_tools',
 'D:\uv',
 'D:\uv\data\memsearch',
 'D:\Git\cmd\git.exe',
 'C:\Program Files\GitHub CLI\gh.exe',
 'D:\FlClash\FlClashCore.exe',
 'D:\DSH-Guard\dsh_kernel_sync.py',
 'D:\DSH-Guard\start_dsh.bat'
)
foreach ($p in $paths) { if (Test-Path $p) { 'OK   ' + $p } else { 'MISS ' + $p } }

Write-Output '=== versions ==='
git --version
gh --version | Select-Object -First 1

Write-Output '=== fltmc ==='
$f = Get-Command fltmc -ErrorAction SilentlyContinue
if ($f) { $f.Source } else { 'NOT FOUND' }

Write-Output '=== subst ==='
subst

Write-Output '=== DNS servers per interface ==='
Get-DnsClientServerAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | ForEach-Object { 'ifIndex=' + $_.InterfaceIndex + ' alias=' + $_.InterfaceAlias + ' servers=' + ($_.ServerAddresses -join ',') }

Write-Output '=== notification policy ==='
$np = Get-ItemProperty 'HKCU:\Software\Policies\Microsoft\Windows\PushNotifications' -ErrorAction SilentlyContinue
if ($np) { 'NoToastApplicationNotification=' + $np.NoToastApplicationNotification } else { 'key not present' }

Write-Output '=== WpnUserService ==='
Get-Service -Name 'WpnUserService*' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name + ' | ' + $_.Status + ' | ' + $_.StartType }

Write-Output '=== git global identity/proxy ==='
git config --global user.name
git config --global user.email
git config --global http.https://github.com.proxy

Write-Output '=== DONE ==='
