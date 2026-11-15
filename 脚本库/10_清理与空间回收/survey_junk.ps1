# 全机垃圾现状盘点
$ErrorActionPreference = 'SilentlyContinue'

function SizeOf($p) {
    if (Test-Path -LiteralPath $p) {
        $m = Get-ChildItem -LiteralPath $p -Recurse -Force -File -ErrorAction SilentlyContinue |
             Measure-Object -Property Length -Sum
        [pscustomobject]@{ 路径 = $p; 文件数 = [int]$m.Count; MB = [math]::Round(($m.Sum) / 1MB, 1) }
    }
    else {
        [pscustomobject]@{ 路径 = $p; 文件数 = 0; MB = 0 }
    }
}

Write-Output '=== 回收站 ==='
$rows = @()
foreach ($k in 'C', 'D', 'E', 'F', 'G', 'H') {
    $rows += SizeOf ($k + ':\$RECYCLE.BIN')
}
$rows | Format-Table -AutoSize

Write-Output '=== 其它垃圾候选 ==='
$cands = @(
    $env:TEMP,
    'C:\Windows\Temp',
    'C:\Windows\Logs',
    'C:\Users\Admin\AppData\Local\CrashDumps',
    'C:\Windows\SoftwareDistribution\Download',
    'C:\$SysReset',
    'C:\Windows.old',
    'C:\Users\Admin\AppData\Local\Microsoft\Windows\Explorer',
    'C:\Users\Admin\AppData\Local\pip\cache'
)
$out = @()
foreach ($c in $cands) { $out += SizeOf $c }
$out | Format-Table -AutoSize

Write-Output '=== 各盘现状 ==='
Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' |
    Select-Object DeviceID, VolumeName,
        @{n = '容量GB'; e = { [math]::Round($_.Size / 1GB, 1) } },
        @{n = '可用GB'; e = { [math]::Round($_.FreeSpace / 1GB, 1) } } |
    Sort-Object DeviceID | Format-Table -AutoSize
