"""Before pushing QoderToolkit: licence terms + secret scan + junk detection.
13k files, so the secret scan is bounded to text files and skips binary blobs.
"""
import os
import re
import sys

sys.stdout.reconfigure(errors="replace")
QT = r"D:\QoderToolkit"
TEXT = {".md", ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".sh",
        ".ps1", ".html", ".css", ".svg", ".csv", ".ini", ".cfg", ".mjs", ".cjs", ".tsx"}
SECRET = [
    (r"sk-[A-Za-z0-9_\-]{20,}", "openai-style key"),
    (r"ghp_[A-Za-z0-9]{30,}", "github PAT"),
    (r"github_pat_[A-Za-z0-9_]{30,}", "github fine-grained PAT"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"xox[baprs]-[A-Za-z0-9\-]{10,}", "slack token"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key"),
    (r"(?i)(api[_-]?key|secret|passwd|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}['\"]", "assigned secret"),
    (r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}", "JWT"),
]
JUNK = {"__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".mypy_cache",
        ".DS_Store", "Thumbs.db", ".ipynb_checkpoints", "dist", "build", ".next"}

print("=== 1. licences ===")
for n in sorted(os.listdir(QT)):
    p = os.path.join(QT, n)
    if not os.path.isdir(p):
        continue
    found = []
    for dp, _, fs in os.walk(p):
        for f in fs:
            if f.upper().startswith(("LICENSE", "NOTICE", "COPYING")):
                fp = os.path.join(dp, f)
                head = open(fp, encoding="utf-8", errors="replace").read(300)
                lines = [l.strip() for l in head.splitlines() if l.strip()][:3]
                found.append("%s: %s" % (f, " | ".join(lines)[:110]))
    print("  %-38s %s" % (n, " ;; ".join(found) if found else "**no licence file**"))

print("\n=== 2. frontmatter licence / source / homepage ===")
for n in sorted(os.listdir(QT)):
    sm = os.path.join(QT, n, "SKILL.md")
    if not os.path.isfile(sm):
        continue
    t = open(sm, encoding="utf-8", errors="replace").read()
    if t.startswith("---"):
        e = t.find("\n---", 3)
        keep = [l.strip() for l in t[3:e].splitlines()
                if re.match(r"^(license|homepage|source|author|version)\s*:", l)]
        if keep:
            print("  %-38s %s" % (n, " | ".join(keep)[:180]))
    for dp, _, fs in os.walk(p):
        pass

print("\n=== 3. PROVENANCE files ===")
for n in sorted(os.listdir(QT)):
    p = os.path.join(QT, n)
    if not os.path.isdir(p):
        continue
    for dp, _, fs in os.walk(p):
        for f in fs:
            if f.upper().startswith("PROVENANCE"):
                txt = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
                print("  %s\\%s: %s" % (n, f, txt[:400].replace("\n", " ")))

print("\n=== 4. junk dirs ===")
hits = []
for dp, ds, fs in os.walk(QT):
    for d in list(ds):
        if d in JUNK:
            full = os.path.join(dp, d)
            cnt = sum(len(f) for _, _, f in os.walk(full))
            byt = sum(os.path.getsize(os.path.join(a, f)) for a, _, fs2 in os.walk(full) for f in fs2)
            hits.append((full, cnt, byt))
            ds.remove(d)
for h, c, b in hits:
    print("  %-80s %5d files %8.2f MB" % (h.replace(QT, "…"), c, b / 1048576))
print("  total junk: %d dirs" % len(hits))

print("\n=== 5. secret scan (text files only) ===")
n_text = n_bin = 0
findings = []
for dp, ds, fs in os.walk(QT):
    ds[:] = [d for d in ds if d not in JUNK and d != ".git"]
    for f in fs:
        fp = os.path.join(dp, f)
        ext = os.path.splitext(f)[1].lower()
        if ext not in TEXT:
            n_bin += 1
            continue
        try:
            if os.path.getsize(fp) > 3_000_000:
                n_bin += 1
                continue
            t = open(fp, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        n_text += 1
        for pat, label in SECRET:
            for m in re.finditer(pat, t):
                ln = t[:m.start()].count("\n") + 1
                findings.append((fp.replace(QT, "…"), ln, label, m.group(0)[:14]))
print("  scanned %d text files, skipped %d binary/large" % (n_text, n_bin))
print("  findings: %d" % len(findings))
for f, ln, label, frag in findings[:40]:
    print("   %s:%d  [%s] %s…" % (f, ln, label, frag))

print("\n=== 6. largest files ===")
allf = []
for dp, ds, fs in os.walk(QT):
    ds[:] = [d for d in ds if d != ".git"]
    for f in fs:
        fp = os.path.join(dp, f)
        try:
            allf.append((os.path.getsize(fp), fp))
        except OSError:
            pass
allf.sort(reverse=True)
for b, fp in allf[:8]:
    print("  %7.2f MB  %s" % (b / 1048576, fp.replace(QT, "…")))
print("  TOTAL %.2f MB in %d files" % (sum(b for b, _ in allf) / 1048576, len(allf)))
