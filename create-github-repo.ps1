# create-github-repo.ps1 - create PRIVATE repo ai-renwu under chicatancau-create via gh.
# Real target: api.github.com (gh CLI). 127.0.0.1:7890 is local exit only, NOT a URL substitution.
$env:HTTPS_PROXY = 'http://127.0.0.1:7890'
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
Write-Output '=== POST create GitHub repo ==='
gh api -X POST user/repos -f name=ai-renwu -f private=true -f auto_init=false -f description='AI renwu workspace scripts backup (dual-push)' --jq '.full_name, .private, .html_url' 2>&1 | ForEach-Object { "$_" }
Write-Output ('POST rc=' + $LASTEXITCODE)
Write-Output '=== GET verify ==='
gh api repos/chicatancau-create/ai-renwu -X GET --jq '.full_name, .private, .html_url' 2>&1 | ForEach-Object { "$_" }
Write-Output ('GET rc=' + $LASTEXITCODE)
