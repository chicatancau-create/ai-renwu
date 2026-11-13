$ErrorActionPreference = 'Continue'

Write-Output '===== 1. GitHub account emails (needs user:email scope; 404 = scope missing, not fatal) ====='
gh api user/emails -X GET 2>&1 | ForEach-Object { "$_" }
Write-Output ("rc=" + $LASTEXITCODE)

Write-Output ''
Write-Output '===== 2. Commit-author evidence: any past commit using chicatancau@gmail.com and linked? ====='
foreach ($r in @('CodeWeave','cc-hud','fullstack-study-library','fullstack-code')) {
  Write-Output ("--- " + $r + " (email <TAB> linked-login; empty login = unlinked)")
  gh api ("repos/chicatancau-create/" + $r + "/commits?per_page=10") -X GET --jq '.[] | [.commit.author.email, .author.login] | @tsv' 2>&1 | ForEach-Object { "$_" }
  Write-Output ("rc=" + $LASTEXITCODE)
}

Write-Output ''
Write-Output '===== 3. Change global user.email to chicatancau@gmail.com ====='
git config --global user.email chicatancau@gmail.com
Write-Output ("rc=" + $LASTEXITCODE)
Write-Output '--- read back:'
git config --global user.email
git config --global user.name

Write-Output ''
Write-Output '===== 4. Local override check (rc=1 means no override, global applies) ====='
foreach ($p in @('E:\fullstack-code','G:\cc-hud','G:\CodeWeave')) {
  Write-Output ("--- " + $p)
  git -C $p config --local user.email 2>&1 | ForEach-Object { "$_" }
  Write-Output ("rc=" + $LASTEXITCODE)
}

Write-Output ''
Write-Output '===== DONE ====='
