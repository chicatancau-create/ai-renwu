$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$hbName = -join ([char]0x672C, [char]0x5730, 'AI', [char]0x4F7F, [char]0x7528, [char]0x624B, [char]0x518C)
$root = Join-Path 'E:\' $hbName
$inboxName = '99-' + (-join ([char]0x6536, [char]0x4EF6, [char]0x7BB1))
$inbox = Join-Path $root $inboxName
$src = @(Get-ChildItem $inbox -Filter '*VSLANG*.md' -File)
if ($src.Count -ne 1) { Write-Output ('ABORT: expected 1 VSLANG source, got ' + $src.Count); exit 1 }
Write-Output ('source: ' + $src[0].FullName)
$oldPrefix = -join ([char]0x5F85, [char]0x9A8C, [char]0x8BC1)
$newPrefix = -join ([char]0x8E29, [char]0x5751)
if (-not $src[0].Name.StartsWith($oldPrefix)) { Write-Output 'ABORT: unexpected prefix'; exit 1 }
$newName = $newPrefix + $src[0].Name.Substring($oldPrefix.Length)
$gen = Get-ChildItem $root -Directory | Where-Object { $_.Name -like '03-*' } | Select-Object -First 1
$dbg = Get-ChildItem $gen.FullName -Directory | Where-Object { $_.Name -like '03-*' } | Select-Object -First 1
$dest = Join-Path $dbg.FullName $newName
Write-Output ('dest: ' + $dest)
if (Test-Path $dest) { Write-Output 'ABORT: dest exists' } else {
  Move-Item -Path $src[0].FullName -Destination $dest
  Write-Output ('moved; src exists=' + (Test-Path $src[0].FullName) + ' dest exists=' + (Test-Path $dest))
}
Write-Output '=== DONE ==='
