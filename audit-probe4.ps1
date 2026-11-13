$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output '=== WARP CLI STATUS ==='
& 'C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe' status 2>&1 | Out-String

Write-Output '=== WARP CLI SETTINGS ==='
& 'C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe' settings 2>&1 | Out-String

Write-Output '=== HIDDEN WARP ADAPTERS ==='
$a = Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*WARP*' -or $_.InterfaceDescription -like '*Cloudflare*' }
if ($a) { $a | Select-Object Name, InterfaceDescription, Status | Format-Table -AutoSize | Out-String -Width 220 } else { Write-Output 'NONE' }

Write-Output '=== PROBE4 DONE ==='
