# 删除前存档：把回收站完整清单写成 CSV（删除后仍可追溯删了什么）
# 用法：archive_recycle_list.ps1 [-Tag 20261116_r3]
#   Tag 只用于文件名后缀，防止覆盖历史存档（历史证据快照不改写）。
param([string]$Tag = (Get-Date -Format 'yyyyMMdd_HHmmss'))
$ErrorActionPreference = 'SilentlyContinue'

# 路径基准：优先用上层目录（任务目录），否则退回脚本所在目录
$Base = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $Base '02_证据日志'))) { $Base = $PSScriptRoot }
$OutDir = Join-Path $Base '02_证据日志'
if (-not (Test-Path -LiteralPath $OutDir)) { $OutDir = Join-Path $env:TEMP 'dsh-cleanup-logs' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$base = $Base
$outDir = (Join-Path $OutDir 'raw')
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$csv = Join-Path $outDir ('回收站清单_删除前_' + $Tag + '.csv')

$rows = @()
foreach ($k in 'C', 'D', 'E', 'F', 'G', 'H') {
    $bin = $k + ':\$RECYCLE.BIN'
    if (-not (Test-Path -LiteralPath $bin)) { continue }
    Get-ChildItem -LiteralPath $bin -Recurse -Force -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $rows += [pscustomobject]@{
                盘       = $k
                文件名   = $_.Name
                字节     = $_.Length
                修改时间 = $_.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
                相对路径 = $_.FullName.Substring($bin.Length)
            }
        }
}

$rows | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8

$total = ($rows | Measure-Object -Property 字节 -Sum).Sum
Write-Output ('清单已存档: ' + $csv)
Write-Output ('条目数 = ' + $rows.Count)
Write-Output ('合计 GB = ' + [math]::Round($total / 1GB, 2))
Write-Output ('CSV 大小 MB = ' + [math]::Round((Get-Item $csv).Length / 1MB, 2))
