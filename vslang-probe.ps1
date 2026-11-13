$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$work = 'G:\AIrenwu\vslang-probe'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$vcvars = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
$cppPath = Join-Path $work 'bad.cpp'
Set-Content -Path $cppPath -Value 'int main() { int x = "hello"; return x; }' -Encoding ASCII

$batA = '@echo off' + "`r`n" + 'set VSLANG=1033' + "`r`n" + 'call "' + $vcvars + '" >nul 2>&1' + "`r`n" + 'cl /c /nologo "' + $cppPath + '" > "' + (Join-Path $work 'logA.txt') + '" 2>&1'
Set-Content -Path (Join-Path $work 'varA.bat') -Value $batA -Encoding ASCII
$batB = '@echo off' + "`r`n" + 'call "' + $vcvars + '" >nul 2>&1' + "`r`n" + 'set VSLANG=1033' + "`r`n" + 'cl /c /nologo "' + $cppPath + '" > "' + (Join-Path $work 'logB.txt') + '" 2>&1'
Set-Content -Path (Join-Path $work 'varB.bat') -Value $batB -Encoding ASCII

cmd /c (Join-Path $work 'varA.bat')
cmd /c (Join-Path $work 'varB.bat')

foreach ($tag in 'A','B') {
  $log = Join-Path $work ('log' + $tag + '.txt')
  if (Test-Path $log) {
    $bytes = [System.IO.File]::ReadAllBytes($log)
    $nonascii = @($bytes | Where-Object { $_ -gt 127 }).Count
    Write-Output ('log' + $tag + ' bytes=' + $bytes.Count + ' nonascii=' + $nonascii)
    $gbk = [System.Text.Encoding]::GetEncoding('GBK').GetString($bytes)
    $lines = ($gbk -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -First 4)
    Write-Output ('log' + $tag + ' sample: ' + ($lines -join ' | '))
  } else { Write-Output ('log' + $tag + ' MISSING') }
}
Write-Output '=== DONE ==='
