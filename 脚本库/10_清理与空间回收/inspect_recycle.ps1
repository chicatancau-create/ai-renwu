# 回收站内容体检：按扩展名 + 按原位置统计，判断是否全是可丢弃内容
$ErrorActionPreference = 'SilentlyContinue'

$drives = 'C', 'D', 'E', 'F', 'G', 'H'
$all = @()
foreach ($k in $drives) {
    $p = $k + ':\$RECYCLE.BIN'
    if (-not (Test-Path -LiteralPath $p)) { continue }
    Get-ChildItem -LiteralPath $p -Recurse -Force -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $all += [pscustomobject]@{
                盘       = $k
                扩展名   = $(if ([string]::IsNullOrWhiteSpace($_.Extension)) { '(无)' } else { $_.Extension.ToLower() })
                字节     = $_.Length
                修改时间 = $_.LastWriteTime
            }
        }
}

Write-Output ('回收站文件总数 = ' + $all.Count)
Write-Output ('回收站合计 GB   = ' + [math]::Round((($all | Measure-Object -Property 字节 -Sum).Sum) / 1GB, 2))
Write-Output ''

Write-Output '=== 按扩展名 Top 15（按体积）==='
$all | Group-Object 扩展名 | ForEach-Object {
    [pscustomobject]@{
        扩展名 = $_.Name
        文件数 = $_.Count
        GB     = [math]::Round((($_.Group | Measure-Object -Property 字节 -Sum).Sum) / 1GB, 2)
    }
} | Sort-Object GB -Descending | Select-Object -First 15 | Format-Table -AutoSize

Write-Output '=== 按盘分组 ==='
$all | Group-Object 盘 | ForEach-Object {
    [pscustomobject]@{
        盘   = $_.Name
        文件数 = $_.Count
        GB   = [math]::Round((($_.Group | Measure-Object -Property 字节 -Sum).Sum) / 1GB, 2)
    }
} | Sort-Object 盘 | Format-Table -AutoSize

Write-Output '=== 最大的 20 个文件 ==='
$all | Sort-Object 字节 -Descending | Select-Object -First 20 |
    ForEach-Object {
        [pscustomobject]@{
            盘     = $_.盘
            MB     = [math]::Round($_.字节 / 1MB, 1)
            扩展名 = $_.扩展名
            修改   = $_.修改时间.ToString('yyyy-MM-dd')
        }
    } | Format-Table -AutoSize

Write-Output '=== 时间分布（按修改年份-月份）==='
$all | Group-Object { $_.修改时间.ToString('yyyy-MM') } | Sort-Object Name |
    ForEach-Object {
        [pscustomobject]@{
            月份   = $_.Name
            文件数 = $_.Count
            GB     = [math]::Round((($_.Group | Measure-Object -Property 字节 -Sum).Sum) / 1GB, 2)
        }
    } | Format-Table -AutoSize
