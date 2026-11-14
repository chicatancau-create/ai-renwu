$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$msvcRoot = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC'
Get-ChildItem $msvcRoot -Directory | ForEach-Object {
  $ver = $_.Name
  $bin = Join-Path $_.FullName 'bin\Hostx64\x64'
  Write-Output ('MSVC ' + $ver + ' bin exists=' + (Test-Path $bin))
  if (Test-Path $bin) {
    Get-ChildItem $bin -Directory | ForEach-Object {
      $ui = Join-Path $_.FullName 'clui.dll'
      Write-Output ('  locale dir ' + $_.Name + ' clui.dll=' + (Test-Path $ui))
    }
    $cl = Join-Path $bin 'cl.exe'
    if (Test-Path $cl) { Write-Output ('  cl.exe version=' + (Get-Item $cl).VersionInfo.FileVersion) }
  }
}
$log = 'G:\AIrenwu\vslang-probe\logA.txt'
if (Test-Path $log) {
  $bytes = [System.IO.File]::ReadAllBytes($log)
  $utf8 = [System.Text.Encoding]::UTF8.GetString($bytes)
  Write-Output ('logA UTF8: ' + (($utf8 -split "`r?`n" | Where-Object { $_.Trim() }) -join ' | '))
}
Write-Output '=== DONE ==='
