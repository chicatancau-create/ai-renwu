# verify-proxy7890.ps1 - prove the live system proxy port actually proxies GitHub API.
$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
$out = gh api user --jq .login 2>&1
Write-Output ('via 7890: rc=' + $LASTEXITCODE + ' out=' + ($out -join ' '))
