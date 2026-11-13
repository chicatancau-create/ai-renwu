$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
$env:HTTP_PROXY = 'http://127.0.0.1:7890'

Write-Output '=== GitHub attribution: CodeWeave branch tip (official API, explicit GET) ==='
gh api 'repos/chicatancau-create/CodeWeave/commits?per_page=1&sha=codex/project-layout-20261106' -X GET --jq '.[0] | .sha, .author.login, .commit.author.email' 2>&1 | ForEach-Object { "$_" }
Write-Output ("rc=" + $LASTEXITCODE)
Write-Output '=== DONE ==='
