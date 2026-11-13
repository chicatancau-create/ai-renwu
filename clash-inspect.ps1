$ErrorActionPreference = 'Continue'
$p = 'C:\ProgramData\clash-verge-service'
Write-Output ('exists: ' + (Test-Path $p))
Write-Output '--- top-level (Force) ---'
try { Get-ChildItem $p -Force -ErrorAction Stop | ForEach-Object { Write-Output ($_.Mode + '  ' + $_.Name) } } catch { Write-Output ('TOPLEVEL ERROR: ' + $_.Exception.Message) }
Write-Output '--- recursive file count (no SilentlyContinue) ---'
try { $f = @(Get-ChildItem $p -Recurse -Force -File -ErrorAction Stop); Write-Output ('filecount: ' + $f.Count) } catch { Write-Output ('RECURSE ERROR: ' + $_.Exception.Message) }
Write-Output '--- ACL ---'
try { $a = Get-Acl $p -ErrorAction Stop; Write-Output ('owner: ' + $a.Owner); Write-Output ($a.Access | Out-String) } catch { Write-Output ('ACL ERROR: ' + $_.Exception.Message) }
Write-Output '--- clash service/process ---'
$svc = @(Get-Service -Name '*clash*' -ErrorAction SilentlyContinue); Write-Output ('clash services: ' + $svc.Count)
$proc = @(Get-Process -Name '*clash*' -ErrorAction SilentlyContinue); Write-Output ('clash processes: ' + $proc.Count)
Write-Output '--- DONE ---'
