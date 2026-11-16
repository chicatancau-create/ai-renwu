# 系统目录清理 worker（需管理员）。由 run-system-cleanup.cmd 以管理员身份调用。
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File system_cleanup_worker.ps1 [-DryRun]
param([switch]$DryRun)
$ErrorActionPreference = 'SilentlyContinue'

# ---- 路径基准：任务目录 / 脚本独立运行 / 兜底 ----
$Base = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $Base '02_证据日志'))) { $Base = $PSScriptRoot }
$OutDir = Join-Path $Base '02_证据日志'
if (-not (Test-Path -LiteralPath $OutDir)) { $OutDir = Join-Path $env:TEMP 'dsh-cleanup-logs' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$mode = if ($DryRun) { 'DRYRUN' } else { 'APPLY' }
$log  = Join-Path $OutDir ('system_cleanup_' + $mode + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.log')
function Say($m) {
    $line = '[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $m
    Write-Host $line
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
}

$isAdmin = $false
try {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $isAdmin = (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch { }

Say '================ 系统目录清理 ================'
Say ('模式: ' + $mode + '    管理员: ' + $isAdmin + '    用户: ' + $env:USERNAME)
Say ('日志: ' + $log)
if (-not $isAdmin) {
    Say '⚠ 当前不是管理员：只能盘点，删除会失败。请用 run-system-cleanup.cmd 双击运行并同意 UAC。'
}
Say ''

function Get-DirStat($p) {
    if (-not (Test-Path -LiteralPath $p)) { return @{ Files = 0; MB = 0.0 } }
    $f = @(Get-ChildItem -LiteralPath $p -Recurse -Force -File -ErrorAction SilentlyContinue)
    $b = 0.0
    foreach ($x in $f) { $b += $x.Length }
    return @{ Files = $f.Count; MB = [math]::Round($b / 1MB, 1) }
}
function Show-Disk($title) {
    Say ('--- ' + $title + ' ---')
    foreach ($k in 'C', 'D', 'E', 'F', 'G', 'H') {
        $d = Get-PSDrive -Name $k -ErrorAction SilentlyContinue
        if ($d -and $d.Free -gt 0) {
            Say ('  ' + $k + ': 可用 ' + [math]::Round($d.Free / 1GB, 2) + ' GB')
        }
    }
}

Show-Disk '清理前各盘可用空间'

# ---- 1. C:\Windows\Logs ----
Say ''
Say '--- 1. C:\Windows\Logs ---'
$p1 = 'C:\Windows\Logs'
$before = Get-DirStat $p1
Say ('清理前: ' + $before.Files + ' 文件 / ' + $before.MB + ' MB')
if (-not $DryRun) {
    $ok = 0; $fail = 0
    # 注意：-Include 配 -LiteralPath/-Recurse 时不过滤（PowerShell 已知坑），必须用 Where-Object 自己筛
    $targets = @(Get-ChildItem -LiteralPath $p1 -Recurse -Force -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in '.log', '.etl', '.txt', '.cab', '.old' })
    Say ('  待删 ' + $targets.Count + ' 个（只删 .log/.etl/.txt/.cab/.old；保留 .evtx/.json/.xml）')
    foreach ($f in $targets) {
        try { Remove-Item -LiteralPath $f.FullName -Force -ErrorAction Stop; $ok++ }
        catch { $fail++ }
    }
    $after = Get-DirStat $p1
    Say ('  删除后: ' + $after.Files + ' 文件 / ' + $after.MB + ' MB（成功 ' + $ok + '，失败 ' + $fail + '）')
    if ($fail -gt 0) { Say '  失败项多为正在写入的日志（waasmedic/CBS 等），属正常；被占用不等于脚本失败。' }
} else {
    $targets = @(Get-ChildItem -LiteralPath $p1 -Recurse -Force -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in '.log', '.etl', '.txt', '.cab', '.old' })
    $sz = 0.0; foreach ($x in $targets) { $sz += $x.Length }
    Say ('  [DryRun] 可删 ' + $targets.Count + ' 个 / ' + [math]::Round($sz / 1MB, 1) + ' MB')
}

# ---- 2. SoftwareDistribution\Download ----
Say ''
Say '--- 2. C:\Windows\SoftwareDistribution\Download（Windows 更新缓存）---'
$p2 = 'C:\Windows\SoftwareDistribution\Download'
$before2 = Get-DirStat $p2
Say ('清理前: ' + $before2.Files + ' 文件 / ' + $before2.MB + ' MB')
if (-not $DryRun) {
    $svc = Get-Service -Name wuauserv -ErrorAction SilentlyContinue
    $wasRunning = $false
    if ($svc -and $svc.Status -eq 'Running') {
        $wasRunning = $true
        Say '  先停 Windows Update 服务（wuauserv）再删，删完恢复...'
        try { Stop-Service -Name wuauserv -Force -ErrorAction Stop; Start-Sleep -Seconds 2 } catch { Say ('  ⚠ 停服务失败: ' + $_.Exception.Message) }
    }
    $ok = 0; $fail = 0
    $targets = @(Get-ChildItem -LiteralPath $p2 -Force -ErrorAction SilentlyContinue)
    foreach ($f in $targets) {
        try { Remove-Item -LiteralPath $f.FullName -Recurse -Force -ErrorAction Stop; $ok++ }
        catch { $fail++ }
    }
    $after = Get-DirStat $p2
    Say ('  删除后: ' + $after.Files + ' 文件 / ' + $after.MB + ' MB（成功 ' + $ok + '，失败 ' + $fail + '）')
    if ($wasRunning) {
        try { Start-Service -Name wuauserv -ErrorAction Stop; Say '  wuauserv 已重新启动' } catch { Say ('  ⚠ 重启动 wuauserv 失败: ' + $_.Exception.Message + '（可重启机器恢复）') }
    }
} else {
    Say '  [DryRun] 将删除该目录下全部内容'
}

# ---- 3. C:\$SysReset ----
Say ''
Say '--- 3. C:\$SysReset（重置/恢复残留）---'
$p3 = 'C:\$SysReset'
$before3 = Get-DirStat $p3
Say ('清理前: ' + $before3.Files + ' 文件 / ' + $before3.MB + ' MB')
if (-not $DryRun) {
    $ok = 0; $fail = 0
    foreach ($f in @(Get-ChildItem -LiteralPath $p3 -Force -ErrorAction SilentlyContinue)) {
        try { Remove-Item -LiteralPath $f.FullName -Recurse -Force -ErrorAction Stop; $ok++ }
        catch { $fail++ }
    }
    $after = Get-DirStat $p3
    Say ('  删除后: ' + $after.Files + ' 文件 / ' + $after.MB + ' MB（成功 ' + $ok + '，失败 ' + $fail + '）')
} else {
    Say '  [DryRun] 将删除该目录下全部内容'
}

# ---- 4. 内存转储文件（可选，C 盘根目录大文件）----
Say ''
Say '--- 4. C:\Windows\MEMORY.DMP / Minidump ---'
foreach ($f in @('C:\Windows\MEMORY.DMP')) {
    if (Test-Path -LiteralPath $f) {
        $sz = [math]::Round((Get-Item -LiteralPath $f -Force).Length / 1MB, 1)
        Say ('  发现 ' + $f + ' = ' + $sz + ' MB')
        if (-not $DryRun) {
            try { Remove-Item -LiteralPath $f -Force -ErrorAction Stop; Say '  已删除' } catch { Say ('  删除失败: ' + $_.Exception.Message) }
        }
    }
}

Show-Disk '清理后各盘可用空间'
Say ''
Say '================ 结束 ================'
Say ('日志已写入: ' + $log)
