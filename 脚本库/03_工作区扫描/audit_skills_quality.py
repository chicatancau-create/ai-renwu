"""Audit D:\\Skills for real optimization opportunities. Read-only, evidence-based.

Checks per skill:
  - frontmatter: name present / matches dir, description present + length, YAML parses
  - description quality: does it say WHEN to use (trigger words) vs just WHAT
  - dead absolute paths referenced in the body (file/dir no longer exists)
  - stale references to pre-move locations (D:\\_整理\\03-项目源码, G:\\AIrenwu\\_scan, ...)
  - body size / structure (has headings? has examples?)
  - duplicate content across skills (identical or near-identical SKILL.md)
  - junk files that should not ship (__pycache__, .pyc, Thumbs.db, editor swap)
  - LICENSE / PROVENANCE presence for third-party skills
  - runtime output written into the skill dir (violates README rule)
"""
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(errors="replace")
LIB = r"D:\Skills"
QODER = r"D:\QoderToolkit"

STALE = [
    r"D:\_整理\03-项目源码",
    r"G:\AIrenwu\_scan",
    r"G:\AIrenwu\_backup",
    r"D:\Skills-disabled\local-ai-handbook-wbai",
    r"E:\XD\_tools",
]
JUNK_NAMES = {"Thumbs.db", "desktop.ini", ".DS_Store"}
JUNK_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ipynb_checkpoints"}
RUNTIME_HINT = re.compile(r"\.(log|tmp|cache|pyc|sqlite|db|lock)$", re.I)


def parse_fm(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:]
    fm = {}
    key = None
    for ln in raw.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", ln)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            if val in ("|", ">", "|-", ">-", "|+", ">+"):
                fm[key] = ""
            else:
                fm[key] = val.strip("'\"")
        elif key and ln.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " + ln.strip()).strip()
    return fm, body


def collect(root):
    out = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        try:
            tag = getattr(os.lstat(p), "st_reparse_tag", 0)
        except OSError:
            tag = 0
        if tag or not os.path.isdir(p):
            continue
        sm = os.path.join(p, "SKILL.md")
        if not os.path.isfile(sm):
            continue
        out.append((name, p, sm))
    return out


skills = collect(LIB)
print("library: %s  (%d skills)" % (LIB, len(skills)))
print("=" * 100)

issues = []
bodies = {}
total_files = 0
total_bytes = 0
junk = []
runtime = []

for name, p, sm in skills:
    text = open(sm, encoding="utf-8", errors="replace").read()
    fm, body = parse_fm(text)
    rec = {"dir": name, "path": p}
    prob = []

    if fm is None:
        prob.append("NO-FRONTMATTER")
        fm = {}
    fmname = fm.get("name", "")
    desc = fm.get("description", "")
    rec["name"] = fmname
    rec["desc_len"] = len(desc)

    if not fmname:
        prob.append("MISSING-name")
    elif fmname != name:
        prob.append("NAME-MISMATCH(%s)" % fmname)
    if not desc:
        prob.append("MISSING-description")
    elif len(desc) > 1024:
        prob.append("DESC-TOO-LONG(%d>1024)" % len(desc))
    elif len(desc) < 40:
        prob.append("DESC-TOO-SHORT(%d)" % len(desc))

    # does description tell WHEN to use?
    when = re.search(r"\b(use|when|whenever|trigger|activate)\b|用于|当|时使用|适用于|触发", desc, re.I)
    if desc and not when:
        prob.append("DESC-NO-TRIGGER")

    # body structure
    heads = re.findall(r"^#{1,3} .+$", body, re.M)
    rec["body_lines"] = body.count("\n") + 1
    rec["headings"] = len(heads)
    if len(heads) < 2:
        prob.append("BODY-NO-STRUCTURE(%d headings)" % len(heads))

    # stale + dead absolute paths in the whole file
    for s in STALE:
        if s in text:
            prob.append("STALE-PATH(%s)" % s)
    for m in re.finditer(r"[A-Za-z]:\\[^\s`'\"<>()\[\]|,;：。，、）]{3,}", text):
        raw = m.group(0).rstrip("\\.,;:")
        if raw.startswith(("D:\\Skills", "D:\\QoderToolkit", "D:\\AI-Tool-State")):
            continue
        if re.search(r"<|\*|\.\.\.|xxx|YYYY|示例|example", raw, re.I):
            continue
        if not os.path.exists(raw):
            prob.append("DEAD-PATH(%s)" % raw)

    # files inventory
    files = []
    for dp, dn, fn in os.walk(p):
        for d in list(dn):
            if d in JUNK_DIRS:
                junk.append(os.path.join(dp, d))
                dn.remove(d)
        for f in fn:
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, p)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                sz = 0
            files.append((rel, sz))
            total_files += 1
            total_bytes += sz
            if f in JUNK_NAMES or f.endswith((".pyc", ".pyo", ".swp", "~")):
                junk.append(fp)
            if RUNTIME_HINT.search(f) and f not in ("catalog.json",):
                runtime.append(fp)
    rec["files"] = len(files)
    rec["bytes"] = sum(s for _, s in files)
    rec["has_license"] = any(os.path.basename(f).upper().startswith("LICENSE") for f, _ in files)
    rec["has_provenance"] = any("PROVENANCE" in f.upper() for f, _ in files)

    h = hashlib.sha256(body.strip().encode("utf-8")).hexdigest()[:16]
    bodies.setdefault(h, []).append(name)
    rec["body_sha"] = h
    rec["problems"] = prob
    issues.append(rec)

print("\n=== A. per-skill problems ===")
nprob = 0
for r in issues:
    if r["problems"]:
        nprob += 1
        print("  %-38s %s" % (r["dir"], "; ".join(r["problems"])))
print("  skills with problems: %d / %d" % (nprob, len(issues)))

print("\n=== B. duplicate bodies ===")
dups = {h: v for h, v in bodies.items() if len(v) > 1}
print("  identical-body groups:", dups if dups else "none")

print("\n=== C. junk files/dirs that should not ship ===")
for j in sorted(set(junk)):
    print("  " + j)
print("  count:", len(set(junk)))

print("\n=== D. runtime artifacts inside skill dirs (README forbids) ===")
for j in sorted(set(runtime)):
    print("  " + j)
print("  count:", len(set(runtime)))

print("\n=== E. third-party skills lacking LICENSE/PROVENANCE ===")
SELF = {"fs-fullstack", "fs-plan", "fs-scaffold", "fs-frontend", "fs-frontend-ui", "fs-backend",
        "fs-database", "fs-testing", "fs-security", "fs-code-review", "fs-performance",
        "fs-deploy", "fs-docs", "vision-tool", "qoder-toolkit", "local-ai-handbook",
        "windows-gui-control", "xd-authoring", "obsidian-vault-validation", "skill-router",
        "headroom"}
for r in issues:
    if r["dir"] in SELF:
        continue
    if not r["has_license"]:
        print("  %-38s no LICENSE  (provenance=%s)" % (r["dir"], r["has_provenance"]))

print("\n=== F. size ranking (top 12) ===")
for r in sorted(issues, key=lambda x: -x["bytes"])[:12]:
    print("  %-38s %8d B  %4d files  desc=%d" % (r["dir"], r["bytes"], r["files"], r["desc_len"]))

print("\n=== G. totals ===")
print("  skills=%d files=%d bytes=%d (%.2f MB)" % (len(issues), total_files, total_bytes, total_bytes / 1048576))

print("\n=== H. QoderToolkit (second library, also to back up?) ===")
for name, p, sm in collect(QODER):
    text = open(sm, encoding="utf-8", errors="replace").read()
    fm, body = parse_fm(text)
    fm = fm or {}
    n = sum(len(f) for _, _, f in os.walk(p))
    b = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(p) for f in fs)
    print("  %-38s name=%-32s files=%5d bytes=%9d desc=%d" %
          (name, fm.get("name", "?"), n, b, len(fm.get("description", ""))))

out = r"G:\AIrenwu\_audit\skill_audit.json"
json.dump(issues, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nwrote", out)
