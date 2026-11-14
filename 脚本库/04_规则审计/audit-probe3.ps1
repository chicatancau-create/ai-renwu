$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output '=== ADAPTERS (name/desc/status/linkspeed) ==='
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed | Format-Table -AutoSize | Out-String -Width 220

Write-Output '=== WARP SERVICE ==='
$svc = Get-Service -Name '*warp*' -ErrorAction SilentlyContinue
if ($svc) { $svc | Select-Object Name, Status, StartType | Format-Table -AutoSize | Out-String } else { Write-Output 'NO WARP SERVICE' }

Write-Output '=== WARP CLI PRESENT ==='
Test-Path 'C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe'

Write-Output '=== WARP OR SPLIT-PREFIX ROUTES (IPv4) ==='
$r = Get-NetRoute -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceAlias -like '*WARP*' -or $_.DestinationPrefix -eq '0.0.0.0/5' -or $_.DestinationPrefix -eq '128.0.0.0/3' -or $_.DestinationPrefix -eq '112.0.0.0/4' -or $_.DestinationPrefix -eq '100.0.0.0/10' }
if ($r) { $r | Select-Object DestinationPrefix, InterfaceAlias, NextHop, RouteMetric | Format-Table -AutoSize | Out-String -Width 220 } else { Write-Output 'NONE' }

Write-Output '=== DNS SERVERS (non-empty, IPv4) ==='
Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object { $_.ServerAddresses.Count -gt 0 } | Select-Object InterfaceAlias, ServerAddresses | Format-Table -AutoSize | Out-String -Width 220

Write-Output '=== DEFAULT ROUTES 0.0.0.0/0 ==='
Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Select-Object InterfaceAlias, NextHop, RouteMetric, InterfaceMetric | Format-Table -AutoSize | Out-String

Write-Output '=== FIND-NETROUTE 8.8.8.8 (real egress) ==='
Find-NetRoute -RemoteIPAddress 8.8.8.8 | Select-Object InterfaceAlias, IPAddress, NextHop | Format-List | Out-String

Write-Output '=== PROBE3 DONE ==='
