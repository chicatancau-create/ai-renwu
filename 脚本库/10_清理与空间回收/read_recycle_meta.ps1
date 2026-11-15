# 读取回收站 $I 元数据，还原大文件的原始路径与文件名
$ErrorActionPreference = 'SilentlyContinue'

function Read-I($iFile) {
    try {
        $b = [System.IO.File]::ReadAllBytes($iFile)
        if ($b.Length -lt 28) { return $null }
        # $I 版本 2：前 8 字节为版本，之后 8 字节原始大小，8 字节删除时间(FILETIME)，4 字节路径长度，随后 UTF-16 路径
        $ver = [BitConverter]::ToInt64($b, 0)
        $size = [BitConverter]::ToInt64($b, 8)
        $len = [BitConverter]::ToInt32($b, 24)
        if ($len -le 0 -or $len -gt 520 -or (28 + $len) -gt $b.Length) { return $null }
        $name = [System.Text.Encoding]::Unicode.GetString($b, 28, $len)
        $name = $name.TrimEnd([char]0)
        return [pscustomobject]@{ 原始路径 = $name; 字节 = $size; 版本 = $ver }
    }
    catch { return $null }
}

$rows = @()
foreach ($k in 'C', 'D', 'E', 'F', 'G', 'H') {
    $bin = $k + ':\$RECYCLE.BIN'
    if (-not (Test-Path -LiteralPath $bin)) { continue }
    Get-ChildItem -LiteralPath $bin -Recurse -Force -File -Filter '$I*' -ErrorAction SilentlyContinue |
        ForEach-Object {
            $meta = Read-I $_.FullName
            if ($meta) {
                $rows += [pscustomobject]@{
                    盘       = $k
                    MB       = [math]::Round($meta.字节 / 1MB, 1)
                    原始路径 = $meta.原始路径
                }
            }
        }
}

Write-Output ('可解析的回收站条目 = ' + $rows.Count)
Write-Output ''
Write-Output '=== 最大的 25 个（按原始大小）==='
$rows | Sort-Object MB -Descending | Select-Object -First 25 | Format-Table -AutoSize

Write-Output '=== ISO 条目 ==='
$rows | Where-Object { $_.原始路径 -match '\.iso$' } | Sort-Object MB -Descending | Format-Table 盘, MB, 原始路径 -AutoSize

Write-Output '=== 体积 >100MB 的条目数 ==='
($rows | Where-Object { $_.MB -gt 100 }).Count
