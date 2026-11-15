# 第二轮垃圾清理：回收站 + 临时文件 + 系统日志（-DryRun 只盘点，-Apply 才真删）
param(
    [switch]$DryRun,
    [switch]$Apply
)
$ErrorActionPreference = 'SilentlyContinue'

# 路径基准：优先用上层目录（任务目录），否则退回脚本所在目录
$Base = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $Base '02_证据日志'))) { $Base = $PSScriptRoot }
$OutDir = Join-Path $Base '02_证据日志'
if (-not (Test-Path -LiteralPath $OutDir)) { $OutDir = Join-Path $env:TEMP 'dsh-cleanup-logs' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if (-not $DryRun -and -not $Apply) { $DryRun = $true }

$base = $Base
$logDir = $OutDir
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$mode  = if ($Apply) { 'APPLY' } else { 'DRYRUN' }
$log = Join-Path $logDir ('cleanup_' + $mode + '_' + $stamp + '.log')

function L($m) {
    $line = '[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $m
    Write-Output $line
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
}

function Fmt($bytes) { return [math]::Round($bytes / 1MB, 1).ToString() + ' MB' }

function Get-FolderStat($path) {
    if (-not (Test-Path -LiteralPath $path)) { return [pscustomobject]@{ Files = 0; Bytes = 0 } }
    $f = @(Get-ChildItem -LiteralPath $path -Recurse -Force -File -ErrorAction SilentlyContinue)
    $sum = 0
    foreach ($x in $f) { $sum += $x.Length }
    return [pscustomobject]@{ Files = $f.Count; Bytes = $sum }
}

function Get-FreeGB($d) {
    $v = Get-CimInstance Win32_LogicalDisk -Filter ("DeviceID='" + $d + ":'") -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $v) { return $null }
    return [math]::Round($v.FreeSpace / 1GB, 2)
}

$drives = @('C', 'D', 'E', 'F', 'G', 'H')

L ('================ 模式: ' + $mode + ' ================')

# ---------- 0. 清理前快照 ----------
L '--- 0. 清理前各盘可用空间 ---'
$before = @{}
foreach ($d in $drives) {
    $g = Get-FreeGB $d
    if ($null -ne $g) { $before[$d] = $g; L ($d + ': 可用 ' + $g + ' GB') }
}

# ---------- 1. 回收站 ----------
L ''
L '--- 1. 回收站 ---'
$binTotalFiles = 0
$binTotalBytes = 0
foreach ($d in $drives) {
    $bin = $d + ':\$RECYCLE.BIN'
    if (-not (Test-Path -LiteralPath $bin)) { L ($d + ': 无 $RECYCLE.BIN'); continue }
    $s = Get-FolderStat $bin
    $binTotalFiles += $s.Files
    $binTotalBytes += $s.Bytes
    L ($d + ': ' + $s.Files + ' 文件 / ' + (Fmt $s.Bytes))
}
L ('回收站合计: ' + $binTotalFiles + ' 文件 / ' + (Fmt $binTotalBytes))

if ($Apply) {
    L '执行 Clear-RecycleBin（逐盘）...'
    foreach ($d in $drives) {
        $bin = $d + ':\$RECYCLE.BIN'
        if (-not (Test-Path -LiteralPath $bin)) { continue }
        $s = Get-FolderStat $bin
        if ($s.Files -eq 0) { continue }
        try {
            Clear-RecycleBin -DriveLetter $d -Force -Confirm:$false -ErrorAction Stop
            L ($d + ': Clear-RecycleBin 返回成功')
        } catch {
            L ($d + ': Clear-RecycleBin 失败 -> ' + $_.Exception.Message)
        }
    }

    L '残渣清扫：直接删 $RECYCLE.BIN 下各 SID 子目录内容（保留目录壳）...'
    foreach ($d in $drives) {
        $bin = $d + ':\$RECYCLE.BIN'
        if (-not (Test-Path -LiteralPath $bin)) { continue }
        $subs = @(Get-ChildItem -LiteralPath $bin -Force -Directory -ErrorAction SilentlyContinue)
        foreach ($sd in $subs) {
            $s = Get-FolderStat $sd.FullName
            if ($s.Files -eq 0) { continue }
            L ($d + ': 残留 ' + $sd.Name + ' = ' + $s.Files + ' 文件 / ' + (Fmt $s.Bytes) + '，开始删除')
            Get-ChildItem -LiteralPath $sd.FullName -Force -ErrorAction SilentlyContinue | ForEach-Object {
                Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }

    L '回收站复核：'
    $afterFiles = 0
    $afterBytes = 0
    foreach ($d in $drives) {
        $bin = $d + ':\$RECYCLE.BIN'
        if (-not (Test-Path -LiteralPath $bin)) { continue }
        $s = Get-FolderStat $bin
        $afterFiles += $s.Files
        $afterBytes += $s.Bytes
        if ($s.Files -gt 0) { L ('  ' + $d + ': 仍剩 ' + $s.Files + ' 文件 / ' + (Fmt $s.Bytes)) }
    }
    L ('  回收站剩余合计: ' + $afterFiles + ' 文件 / ' + (Fmt $afterBytes))
}

# ---------- 2. 临时文件 ----------
L ''
L '--- 2. 临时文件 ---'
$tempPaths = @(
    @{ Name = '用户 %TEMP%'; Path = $env:TEMP },
    @{ Name = 'C:\Windows\Temp'; Path = 'C:\Windows\Temp' },
    @{ Name = 'CrashDumps'; Path = (Join-Path $env:LOCALAPPDATA 'CrashDumps') }
)
foreach ($t in $tempPaths) {
    if (-not $t.Path) { continue }
    $s = Get-FolderStat $t.Path
    L ($t.Name + ' (' + $t.Path + '): ' + $s.Files + ' 文件 / ' + (Fmt $s.Bytes))
    if ($Apply -and $s.Files -gt 0) {
        $ok = 0
        $fail = 0
        Get-ChildItem -LiteralPath $t.Path -Force -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction Stop
                $ok++
            } catch {
                $fail++
            }
        }
        $s2 = Get-FolderStat $t.Path
        L ('  删除后: ' + $s2.Files + ' 文件 / ' + (Fmt $s2.Bytes) + '（成功条目 ' + $ok + '，被占用/失败 ' + $fail + '）')
    }
}

# ---------- 3. C:\Windows\Logs ----------
L ''
L '--- 3. C:\Windows\Logs ---'
$wl = 'C:\Windows\Logs'
$s = Get-FolderStat $wl
L ('清理前: ' + $s.Files + ' 文件 / ' + (Fmt $s.Bytes))
if ($Apply -and $s.Files -gt 0) {
    $ok = 0
    $fail = 0
    Get-ChildItem -LiteralPath $wl -Recurse -Force -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in @('.log', '.etl', '.txt', '.cab', '.evtx') -or $_.Name -like '*.old' } |
        ForEach-Object {
            try {
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop
                $ok++
            } catch {
                $fail++
            }
        }
    $s2 = Get-FolderStat $wl
    L ('  删除后: ' + $s2.Files + ' 文件 / ' + (Fmt $s2.Bytes) + '（成功 ' + $ok + '，失败 ' + $fail + '）')
}

# ---------- 4. 其他小候选 ----------
L ''
L '--- 4. 其他候选 ---'
$misc = @(
    @{ Name = 'SoftwareDistribution\Download'; Path = 'C:\Windows\SoftwareDistribution\Download' },
    @{ Name = 'C:\$SysReset'; Path = 'C:\$SysReset' },
    @{ Name = 'C:\Windows\Prefetch'; Path = 'C:\Windows\Prefetch' },
    @{ Name = 'WER ReportQueue'; Path = 'C:\ProgramData\Microsoft\Windows\WER\ReportQueue' },
    @{ Name = 'WER ReportArchive'; Path = 'C:\ProgramData\Microsoft\Windows\WER\ReportArchive' }
)
foreach ($m in $misc) {
    $s = Get-FolderStat $m.Path
    L ($m.Name + ': ' + $s.Files + ' 文件 / ' + (Fmt $s.Bytes))
    if ($Apply -and $s.Files -gt 0) {
        Get-ChildItem -LiteralPath $m.Path -Force -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
        $s2 = Get-FolderStat $m.Path
        L ('  删除后: ' + $s2.Files + ' 文件 / ' + (Fmt $s2.Bytes))
    }
}

# ---------- 5. 清理后复核 ----------
L ''
L '--- 5. 清理后各盘可用空间 ---'
$gainTotal = 0
foreach ($d in $drives) {
    $g = Get-FreeGB $d
    if ($null -ne $g) {
        $diff = if ($before.ContainsKey($d)) { [math]::Round($g - $before[$d], 2) } else { 0 }
        if ($diff -gt 0) { $gainTotal += $diff }
        L ($d + ': 可用 ' + $g + ' GB （变化 +' + $diff + ' GB）')
    }
}
L ('合计新增可用 ≈ ' + [math]::Round($gainTotal, 2) + ' GB')
L ('日志文件: ' + $log)
L '================ 结束 ================'
