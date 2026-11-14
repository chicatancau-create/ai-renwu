$ErrorActionPreference = 'Continue'
$p = 'C:\ProgramData\clash-verge-service'
Write-Output ('exists: ' + (Test-Path $p))
# 2026-11-13: every enumeration is now guarded by Test-Path. PS quirk observed today:
# Get-ChildItem <nonexistent-leaf> -Recurse treats the leaf as a FILTER and walks the
# PARENT instead - here it recursed C:\ProgramData and reported the denied junction
# 'C:\ProgramData\Application Data'. That yields a count/denial for a DIFFERENT tree,
# which is exactly the kind of artifact that must never feed a delete decision.
if (Test-Path $p) {
  Write-Output '--- top-level (Force) ---'
  try { Get-ChildItem $p -Force -ErrorAction Stop | ForEach-Object { Write-Output ($_.Mode + '  ' + $_.Name) } } catch { Write-Output ('TOPLEVEL ERROR: ' + $_.Exception.Message) }
  Write-Output '--- recursive file count (no SilentlyContinue) ---'
  try { $f = @(Get-ChildItem $p -Recurse -Force -File -ErrorAction Stop); Write-Output ('filecount: ' + $f.Count) } catch { Write-Output ('RECURSE ERROR (UNREADABLE, not empty): ' + $_.Exception.Message) }
  Write-Output '--- ACL ---'
  try { $a = Get-Acl $p -ErrorAction Stop; Write-Output ('owner: ' + $a.Owner); Write-Output ($a.Access | Out-String) } catch { Write-Output ('ACL ERROR: ' + $_.Exception.Message) }
} else {
  Write-Output '--- enumeration skipped: path not present (admin-verified deleted 2026-11-13) ---'
}
# 2026-11-13: precise names. '*clash*' ALSO matches the current proxy FlClash /
# FlClashCore, which made this script report "clash processes: 2" while Clash Verge
# was in fact gone. Judge Verge liveness by *verge* / *mihomo*, and list FlClash
# separately so it is never mistaken for a Verge残留.
Write-Output '--- Verge service/process (precise; *clash* would also match FlClash) ---'
$svc = @(Get-Service -Name '*verge*','*mihomo*' -ErrorAction SilentlyContinue); Write-Output ('verge/mihomo services: ' + $svc.Count)
$proc = @(Get-Process -Name '*verge*','*mihomo*' -ErrorAction SilentlyContinue); Write-Output ('verge/mihomo processes: ' + $proc.Count)
$fl = @(Get-Process -Name 'FlClash','FlClashCore' -ErrorAction SilentlyContinue)
foreach ($x in $fl) { Write-Output ('current proxy (NOT Verge): ' + $x.ProcessName + ' pid=' + $x.Id) }
Write-Output '--- DONE ---'
