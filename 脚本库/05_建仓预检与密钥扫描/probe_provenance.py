"""Identify REAL provenance instead of guessing: licence text, clawx metadata,
upstream URLs inside SKILL.md, and cc-switch's own repo_owner/repo_name columns.
"""
import os
import re
import shutil
import sqlite3
import sys

sys.stdout.reconfigure(errors="replace")
LIB = r"D:\Skills"
URL = re.compile(r"https?://(?:github\.com|gitlab\.com|gitee\.com|gitcode\.com|npmjs\.com|pypi\.org)/[\w./\-]+")

print("=== 1. LICENSE / NOTICE first lines ===")
for n in sorted(os.listdir(LIB)):
    p = os.path.join(LIB, n)
    if not os.path.isdir(p):
        continue
    for dp, _, fs in os.walk(p):
        for f in fs:
            if f.upper().startswith(("LICENSE", "NOTICE")):
                fp = os.path.join(dp, f)
                try:
                    head = open(fp, encoding="utf-8", errors="replace").read(400)
                except OSError as e:
                    head = "ERR %s" % e
                lines = [l.strip() for l in head.splitlines() if l.strip()][:4]
                print("  %-38s %-14s %s" % (n, f, " | ".join(lines)[:150]))

print("\n=== 2. .clawx-preinstalled.json / _skillhub_meta.json / PROVENANCE ===")
for n in sorted(os.listdir(LIB)):
    p = os.path.join(LIB, n)
    if not os.path.isdir(p):
        continue
    for dp, _, fs in os.walk(p):
        for f in fs:
            if f in (".clawx-preinstalled.json", "_skillhub_meta.json") or f.upper().startswith("PROVENANCE"):
                fp = os.path.join(dp, f)
                txt = open(fp, encoding="utf-8", errors="replace").read()
                print("  %s\\%s (%dB): %s" % (n, f, len(txt), txt[:300].replace("\n", " ")))

print("\n=== 3. upstream URLs inside SKILL.md ===")
for n in sorted(os.listdir(LIB)):
    sm = os.path.join(LIB, n, "SKILL.md")
    if not os.path.isfile(sm):
        continue
    t = open(sm, encoding="utf-8", errors="replace").read()
    hits = sorted(set(URL.findall(t)))
    hits = [h for h in hits if "example" not in h.lower()][:4]
    if hits:
        print("  %-38s %s" % (n, " ; ".join(hits)))

print("\n=== 4. cc-switch skills table repo provenance ===")
src = r"C:\Users\Admin\.cc-switch\cc-switch.db"
dst = r"G:\AIrenwu\_audit\ccswitch_prov.db"
try:
    shutil.copy2(src, dst)
    con = sqlite3.connect(dst)
    cur = con.execute("SELECT id,name,directory,repo_owner,repo_name,repo_branch FROM skills ORDER BY id")
    for r in cur.fetchall():
        print("  %-28s dir=%-22s repo=%s/%s@%s" % (r[0], r[2], r[3] or "-", r[4] or "-", r[5] or "-"))
    con.close()
except Exception as e:
    print("  ERR", type(e).__name__, e)

print("\n=== 5. frontmatter extra fields (author/version/license/homepage/source) ===")
for n in sorted(os.listdir(LIB)):
    sm = os.path.join(LIB, n, "SKILL.md")
    if not os.path.isfile(sm):
        continue
    t = open(sm, encoding="utf-8", errors="replace").read()
    if not t.startswith("---"):
        continue
    e = t.find("\n---", 3)
    raw = t[3:e]
    keep = [l.strip() for l in raw.splitlines()
            if re.match(r"^(author|version|license|homepage|source|repository|metadata|allowed-tools)\s*:", l)]
    if keep:
        print("  %-38s %s" % (n, " | ".join(keep)[:200]))
