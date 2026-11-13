# diag-github-push.ps1 - why did push to origin fail with TLS 0A000126?
# Read-only. No credential mutation: ls-remote is a pure fetch and never triggers
# credential reject; NEVER use push --dry-run for probing (it can delete credentials).
# URLs come from the repo's real git remote config; 127.0.0.1:7890 is the LOCAL
# EGRESS only (gh still talks to api.github.com) - no address substitution.
# ASCII-only. Run: powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\diag-github-push.ps1
$ErrorActionPreference = 'Continue'
Set-Location 'G:\AIrenwu'

Write-Output '=== 1. proxy port 7890 real TCP handshake (gold standard) ==='
$t = Test-NetConnection -ComputerName 127.0.0.1 -Port 7890 -WarningAction SilentlyContinue
Write-Output ('TcpTestSucceeded=' + $t.TcpTestSucceeded)

Write-Output '=== 2. 7890 entries (NO State filter - State can be BLANK) + owner ==='
$c = @(Get-NetTCPConnection -LocalPort 7890 -ErrorAction SilentlyContinue)
Write-Output ('entries=' + $c.Count)
$c | Select-Object -First 4 | ForEach-Object {
  $pr = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  Write-Output ('  local=' + $_.LocalAddress + ' state=[' + $_.State + '] pid=' + $_.OwningProcess + ' name=' + $pr.ProcessName + ' path=' + $pr.Path)
}

Write-Output '=== 3. FlClash processes (current proxy) ==='
Get-Process -Name 'FlClash','FlClashCore' -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ('  ' + $_.ProcessName + ' pid=' + $_.Id + ' path=' + $_.Path) }

Write-Output '=== 4. git proxy config + real remotes ==='
git config --global --get http.https://github.com.proxy
git remote -v

Write-Output '=== 5. system proxy registry ==='
$k = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
Write-Output ('ProxyEnable=' + $k.ProxyEnable + ' ProxyServer=' + $k.ProxyServer)

Write-Output '=== 6. minimal real request via gh (api.github.com, egress 7890) ==='
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
gh api user -X GET --jq .login 2>&1
Write-Output ('gh rc=' + $LASTEXITCODE)

Write-Output '=== 7. ls-remote origin (pure fetch, no credential-reject risk) ==='
$env:GIT_TERMINAL_PROMPT = '0'
git -c credential.interactive=false ls-remote origin refs/heads/main 2>&1
Write-Output ('ls-remote rc=' + $LASTEXITCODE)
Write-Output '=== DONE ==='
