# 按原始路径前缀，从回收站精确还原指定条目
# 用途：补回被误删/漏归档的小体积有用内容（不碰大件）
$ErrorActionPreference = 'SilentlyContinue'

# 路径基准：优先用上层目录（任务目录），否则退回脚本所在目录
$Base = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $Base '02_证据日志'))) { $Base = $PSScriptRoot }
$OutDir = Join-Path $Base '02_证据日志'
if (-not (Test-Path -LiteralPath $OutDir)) { $OutDir = Join-Path $env:TEMP 'dsh-cleanup-logs' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$outLog = (Join-Path $OutDir 'restore_selected.log')
function L($m) { Write-Output $m; Add-Content -LiteralPath $outLog -Value $m -Encoding UTF8 }

# 前缀 -> 目标根目录
$rules = @(
    @{ Prefix = 'G:\AIrenwu\2026-11-11_Doubao-uninstall\03_工具脚本\';                    Dest = 'G:\AIrenwu\01_任务归档\2026-11-11_Doubao-uninstall\03_工具脚本' },
    @{ Prefix = 'G:\AIrenwu\2026-11-11_Doubao-uninstall\01_报告\';                          Dest = 'G:\AIrenwu\01_任务归档\2026-11-11_Doubao-uninstall\01_报告' },
    @{ Prefix = 'G:\AIrenwu\01_任务归档\2026-11-02_EndfieldChargePlus恢复\';                Dest = 'G:\AIrenwu\01_任务归档\2026-11-02_EndfieldChargePlus恢复' }
)

function Read-I($iPath) {
    try {
        $bytes = [System.IO.File]::ReadAllBytes($iPath)
        if ($bytes.Length -lt 28) { return $null }
        $pathLen = [System.BitConverter]::ToInt32($bytes, 24)
        if ($pathLen -le 0 -or $pathLen -gt 32767) {
            $raw = [System.Text.Encoding]::Unicode.GetString($bytes, 24, 520)
            return $raw.Split([char]0)[0]
        }
        return [System.Text.Encoding]::Unicode.GetString($bytes, 28, ($pathLen - 1) * 2)
    } catch { return $null }
}

L '===== 定向还原开始 ====='

$candidates = @()
foreach ($d in @('C', 'D', 'E', 'F', 'G', 'H')) {
    $bin = $d + ':\$RECYCLE.BIN'
    if (-not (Test-Path -LiteralPath $bin)) { continue }
    foreach ($sid in @(Get-ChildItem -LiteralPath $bin -Force -Directory -ErrorAction SilentlyContinue)) {
        foreach ($i in @(Get-ChildItem -LiteralPath $sid.FullName -Force -File -ErrorAction SilentlyContinue | Where-Object { $_.Name.StartsWith('$I') })) {
            $op = Read-I $i.FullName
            if ([string]::IsNullOrWhiteSpace($op)) { continue }
            $candidates += [pscustomobject]@{
                原始路径 = $op
                回收站R  = (Join-Path $sid.FullName ('$R' + $i.Name.Substring(2)))
            }
        }
    }
}
L ('回收站可解析条目: ' + $candidates.Count)

$done = 0
$skip = 0
$fail = 0

foreach ($rule in $rules) {
    $hits = @($candidates | Where-Object { $_.原始路径.StartsWith($rule.Prefix, [System.StringComparison]::OrdinalIgnoreCase) })
    L ''
    L ('--- 规则: ' + $rule.Prefix + '  （命中 ' + $hits.Count + ' 条）')
    foreach ($h in $hits) {
        if (-not (Test-Path -LiteralPath $h.回收站R)) { L ('  [无 $R，跳过] ' + $h.原始路径); $skip++; continue }
        $item = Get-Item -LiteralPath $h.回收站R -Force
        if ($item.PSIsContainer) { L ('  [是目录，跳过] ' + $h.原始路径); $skip++; continue }

        $rel = $h.原始路径.Substring($rule.Prefix.Length).TrimStart('\')
        $destFile = Join-Path $rule.Dest $rel
        if (Test-Path -LiteralPath $destFile) { L ('  [已存在，跳过] ' + $rel); $skip++; continue }

        $destParent = Split-Path -Parent $destFile
        New-Item -ItemType Directory -Force -Path $destParent | Out-Null
        Copy-Item -LiteralPath $h.回收站R -Destination $destFile -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $destFile) {
            $a = (Get-Item -LiteralPath $destFile).Length
            if ($a -eq $item.Length) { L ('  [OK] ' + $rel + '  (' + [math]::Round($a / 1KB, 1) + ' KB)'); $done++ }
            else { L ('  [大小不符] ' + $rel); $fail++ }
        } else {
            L ('  [复制失败] ' + $rel); $fail++
        }
    }
}

L ''
L ('结果: 还原 ' + $done + '，跳过 ' + $skip + '，失败 ' + $fail)
L '===== 结束 ====='
