$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output '=== E:\XD existence ==='
if (Test-Path 'E:\XD') {
  'E:\XD EXISTS'
  Get-ChildItem 'E:\XD' -Directory -ErrorAction SilentlyContinue | Select-Object -First 20 | ForEach-Object { $_.Name }
} else { 'E:\XD MISSING' }

Write-Output '=== E:\ root dirs ==='
Get-ChildItem 'E:\' -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }

Write-Output '=== G:\ root dirs ==='
Get-ChildItem 'G:\' -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }

Write-Output '=== XD-like dirs on C/D roots ==='
foreach ($d in @('C:\','D:\')) {
  Get-ChildItem $d -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*XD*' } | ForEach-Object { $_.FullName }
}

Write-Output '=== effective route to 8.8.8.8 ==='
Find-NetRoute -RemoteIPAddress '8.8.8.8' -ErrorAction SilentlyContinue | Select-Object -First 2 | ForEach-Object { 'localIP=' + $_.IPAddress + ' ifIndex=' + $_.InterfaceIndex + ' nextHop=' + $_.NextHop }

Write-Output '=== DONE ==='
