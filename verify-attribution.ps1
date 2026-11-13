$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
$env:HTTP_PROXY = 'http://127.0.0.1:7890'

Write-Output '=== final-tree check: pages non-empty at HEAD ==='
$p = 'E:\fullstack-code'
$s1 = git -C $p cat-file -s 'HEAD:Harmony/harmonyMall-master/entry/src/main/ets/pages/me/RegPage.ets'
Write-Output ("RegPage.ets bytes at HEAD=" + $s1)
$s2 = git -C $p cat-file -s 'HEAD:Harmony/harmonyMall-master/entry/src/main/ets/pages/test/DialogPage.ets'
Write-Output ("DialogPage.ets bytes at HEAD=" + $s2)

Write-Output ''
Write-Output '=== GitHub attribution: fullstack-code latest commit (official API, explicit GET) ==='
gh api 'repos/chicatancau-create/fullstack-code/commits?per_page=1' -X GET --jq '.[0] | .author.login, .commit.author.email' 2>&1 | ForEach-Object { "$_" }
Write-Output ("rc=" + $LASTEXITCODE)

Write-Output ''
Write-Output '=== GitHub attribution: cc-hud latest commit ==='
gh api 'repos/chicatancau-create/cc-hud/commits?per_page=1' -X GET --jq '.[0] | .author.login, .commit.author.email' 2>&1 | ForEach-Object { "$_" }
Write-Output ("rc=" + $LASTEXITCODE)
Write-Output '=== DONE ==='
