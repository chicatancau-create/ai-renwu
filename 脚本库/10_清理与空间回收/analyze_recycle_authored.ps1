# 解析全部回收站 $I 元数据，找出「可能含用户原创内容」的条目
# 输出 UTF-8 文件，避免控制台代码页截断中文路径
$ErrorActionPreference = 'SilentlyContinue'

# 路径基准：优先用上层目录（任务目录），否则退回脚本所在目录
$Base = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $Base '02_证据日志'))) { $Base = $PSScriptRoot }
$OutDir = Join-Path $Base '02_证据日志'
if (-not (Test-Path -LiteralPath $OutDir)) { $OutDir = Join-Path $env:TEMP 'dsh-cleanup-logs' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$outDir = (Join-Path $OutDir 'raw')
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$csvAll  = Join-Path $outDir '回收站原始路径_全量.csv'
$rptFile = Join-Path $outDir '回收站原创内容排查报告.txt'

$authored = @('.md', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.pdf',
              '.py', '.ps1', '.js', '.ts', '.json', '.bat', '.sh', '.cmd',
              '.txt', '.csv', '.sql', '.html', '.css', '.vue', '.java',
              '.c', '.cpp', '.h', '.go', '.rs', '.ino', '.ipynb', '.yaml', '.yml', '.toml')
$installer = @('.exe', '.msi', '.zip', '.7z', '.rar', '.iso', '.msix', '.appx')

$all = @()

function Read-I($iPath, $sidDir) {
    try {
        $bytes = [System.IO.File]::ReadAllBytes($iPath)
        if ($bytes.Length -lt 28) { return $null }
        $origSize = [System.BitConverter]::ToInt64($bytes, 8)
        $pathLen  = [System.BitConverter]::ToInt32($bytes, 24)
        if ($pathLen -le 0 -or $pathLen -gt 32767) {
            $raw = [System.Text.Encoding]::Unicode.GetString($bytes, 24, 520)
            $origPath = $raw.Split([char]0)[0]
        } else {
            $origPath = [System.Text.Encoding]::Unicode.GetString($bytes, 28, ($pathLen - 1) * 2)
        }
        if ([string]::IsNullOrWhiteSpace($origPath)) { return $null }
        $name = Split-Path -Leaf $origPath
        $rPath = Join-Path $sidDir ('$R' + [System.IO.Path]::GetFileName($iPath).Substring(2))
        $isDir = $false
        if (Test-Path -LiteralPath $rPath) { $isDir = (Get-Item -LiteralPath $rPath -Force).PSIsContainer }
        return [pscustomobject]@{
            原始路径 = $origPath
            名称     = $name
            扩展名   = ([System.IO.Path]::GetExtension($name)).ToLower()
            大小     = $origSize
            是否目录 = $isDir
            盘       = $sidDir.Substring(0, 1)
        }
    } catch { return $null }
}

foreach ($d in @('C', 'D', 'E', 'F', 'G', 'H')) {
    $bin = $d + ':\$RECYCLE.BIN'
    if (-not (Test-Path -LiteralPath $bin)) { continue }
    foreach ($sid in @(Get-ChildItem -LiteralPath $bin -Force -Directory -ErrorAction SilentlyContinue)) {
        foreach ($i in @(Get-ChildItem -LiteralPath $sid.FullName -Force -File -ErrorAction SilentlyContinue | Where-Object { $_.Name.StartsWith('$I') })) {
            $r = Read-I $i.FullName $sid.FullName
            if ($r) { $all += $r }
        }
    }
}

$all | Export-Csv -LiteralPath $csvAll -NoTypeInformation -Encoding UTF8

# ---- 报告 ----
$lines = New-Object System.Collections.Generic.List[string]
function W($s) { $lines.Add([string]$s) }

W '================ 回收站原创内容排查 ================'
W ('解析条目总数: ' + $all.Count)
W ''

# 1. 按扩展名分布
W '---------- 1. 按扩展名分布（前 25）----------'
$byExt = $all | Group-Object 扩展名 | Sort-Object { -($_.Group | Measure-Object -Property 大小 -Sum).Sum } | Select-Object -First 25
foreach ($g in $byExt) {
    $s = ($g.Group | Measure-Object -Property 大小 -Sum).Sum
    W ('  ' + $g.Name.PadRight(10) + ' 条目 ' + ([string]$g.Count).PadLeft(6) + '   ' + [math]::Round($s / 1MB, 1) + ' MB')
}
W ''

# 2. 目录类条目（文件夹被整体删除，可能含原创内容）
W '---------- 2. 被删除的目录条目（>50MB，按大小倒序）----------'
$dirs = $all | Where-Object { $_.是否目录 -and $_.大小 -gt 50MB } | Sort-Object 大小 -Descending
W ('  目录条目共 ' + ($all | Where-Object { $_.是否目录 }).Count + ' 个，其中 >50MB 的 ' + $dirs.Count + ' 个：')
foreach ($x in ($dirs | Select-Object -First 40)) {
    W ('  ' + ([math]::Round($x.大小 / 1MB, 1)).ToString().PadLeft(9) + ' MB  ' + $x.盘 + ': ' + $x.原始路径)
}
W ''

# 3. 非安装包、非构建产物的大文件
W '---------- 3. 疑似原创内容条目（文档/源码/笔记类扩展名）----------'
$auth = $all | Where-Object { $authored -contains $_.扩展名 }
W ('  条目数: ' + $auth.Count)
$authBig = $auth | Sort-Object 大小 -Descending | Select-Object -First 40
foreach ($x in $authBig) {
    W ('  ' + ([math]::Round($x.大小 / 1MB, 1)).ToString().PadLeft(9) + ' MB  ' + $x.盘 + ': ' + $x.原始路径)
}
W ''

# 4. 按顶层目录聚合（前两级），看哪些位置被整体清掉
W '---------- 4. 被删内容的来源顶层目录聚合 ----------'
$groups = @{}
foreach ($x in $all) {
    $parts = $x.原始路径 -split '\\'
    if ($parts.Count -ge 2) {
        $key = $parts[0] + '\' + $parts[1]
    } else {
        $key = $x.原始路径
    }
    if (-not $groups.ContainsKey($key)) { $groups[$key] = @{ Count = 0; Bytes = 0 } }
    $groups[$key].Count++
    $groups[$key].Bytes += $x.大小
}
$top = $groups.GetEnumerator() | Sort-Object { -$_.Value.Bytes } | Select-Object -First 25
foreach ($g in $top) {
    W ('  ' + ([math]::Round($g.Value.Bytes / 1MB, 1)).ToString().PadLeft(10) + ' MB  ' + ([string]$g.Value.Count).PadLeft(6) + ' 条   ' + $g.Key)
}
W ''
W '================ 结束 ================'

[System.IO.File]::WriteAllLines($rptFile, $lines, (New-Object System.Text.UTF8Encoding($true)))

Write-Output ('全量CSV: ' + $csvAll)
Write-Output ('报告: ' + $rptFile)
Write-Output ('解析条目数: ' + $all.Count)
