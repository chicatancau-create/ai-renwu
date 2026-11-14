# verify-github2.ps1 - retry GitHub live check with PS-5.1-safe argument passing.
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
function Section([string]$t) { Write-Output ''; Write-Output ('===== ' + $t + ' =====') }

Section 'system proxy settings (HKCU, read-only)'
$is = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
Write-Output ('ProxyEnable=' + $is.ProxyEnable + ' ProxyServer=' + $is.ProxyServer + ' AutoConfigURL=' + $is.AutoConfigURL)

Section 'proxy-like processes running?'
Get-Process | Where-Object { $_.Name -match 'clash|verge|v2ray|sing|mihomo|xray|shadowsocks|ssr|netch|qv2ray' } | Select-Object Name, Id | Format-Table -AutoSize | Out-String

Section 'gh api user DIRECT (simple jq)'
$out = gh api user --jq .login 2>&1
$rc = $LASTEXITCODE
Write-Output ('rc=' + $rc)
Write-Output ($out -join "`n")

if ($rc -ne 0 -and $is.ProxyEnable -eq 1 -and $is.ProxyServer) {
  $p = 'http://' + $is.ProxyServer
  Write-Output ('--- direct failed, retry via system proxy ' + $p)
  $env:HTTPS_PROXY = $p
  $env:HTTP_PROXY = $p
  $out = gh api user --jq .login 2>&1
  Write-Output ('rc=' + $LASTEXITCODE)
  Write-Output ($out -join "`n")
}

Section 'commit attribution: fullstack-code latest commit'
gh api repos/chicatancau-create/fullstack-code/commits -f per_page=1 --jq '.[0].commit.author.email' 2>&1
gh api repos/chicatancau-create/fullstack-code/commits -f per_page=1 --jq '.[0].author.login' 2>&1
Section 'DONE'
