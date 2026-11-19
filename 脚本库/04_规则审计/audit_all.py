# -*- coding: utf-8 -*-
"""Full health audit of the skill-routing + token-saving installation.

Read-only. Prints PASS / WARN / FAIL per check with evidence.
Nothing here mutates state; fixes are applied separately after review.
"""
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOME = r"C:\Users\Admin"
LIB = r"D:\Skills"
ACTIVE = r"D:\Skills-active"
DISABLED = r"D:\Skills-disabled"
QTK = r"D:\QoderToolkit"
ROUTER = os.path.join(LIB, "skill-router")
HR = r"D:\uv\bin\headroom.exe"
PY = sys.executable
HFHUB = r"D:\uv\data\huggingface\hub"
HRLOG = os.path.join(HOME, ".headroom", "logs", "proxy-8787.log")
CCLOG = os.path.join(HOME, ".cc-switch", "logs", "cc-switch.log")

RESULTS = []


def rec(level, name, detail):
    RESULTS.append((level, name, detail))
    print("%-4s %-46s %s" % (level, name, detail))


def reparse(p):
    try:
        return getattr(os.lstat(p), "st_reparse_tag", 0)
    except OSError:
        return None


def target(p):
    try:
        return os.readlink(p)
    except OSError:
        return ""


def tcp(port, t=1.5):
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=t)
        s.close()
        return True
    except OSError:
        return False


def http(url, t=8, data=None, hdr=None):
    req = urllib.request.Request(url, data=data, headers=hdr or {})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read().decode("utf-8", "replace"), int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400], int((time.time() - t0) * 1000)
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e), int((time.time() - t0) * 1000)


def fm(path):
    """Return (name, description) from YAML frontmatter, or (None, None)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except OSError:
        return None, None
    if not txt.startswith("---"):
        return None, None
    end = txt.find("\n---", 3)
    if end < 0:
        return None, None
    block = txt[3:end]
    name = desc = None
    lines = block.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"^(name|description):\s*(.*)$", ln)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in ("|", ">", "|-", ">-", ""):
            buf = []
            for nxt in lines[i + 1:]:
                if re.match(r"^\S", nxt):
                    break
                buf.append(nxt.strip())
            val = " ".join(buf).strip()
        val = val.strip("'\"")
        if key == "name":
            name = val
        else:
            desc = val
    return name, desc


print("=" * 100)
print("A. headroom proxy")
print("=" * 100)
ok8787 = tcp(8787)
rec("PASS" if ok8787 else "FAIL", "8787 TCP listening", str(ok8787))
st, body, ms = http("http://127.0.0.1:8787/health")
healthy = st == 200 and '"healthy"' in body
rec("PASS" if healthy else "FAIL", "8787 /health", "%s %sms %s" % (st, ms, body[:150]))
st2, b2, _ = http("http://127.0.0.1:15721/health")
rec("PASS" if st2 == 200 else "FAIL", "15721 cc-switch /health", "%s %s" % (st2, b2[:110]))

man = os.path.join(HOME, ".headroom", "deploy", "default", "manifest.json")
if os.path.isfile(man):
    with open(man, encoding="utf-8") as f:
        M = json.load(f)
    env = M.get("base_env", {}) or {}
    need = {
        "ANTHROPIC_TARGET_API_URL": "http://127.0.0.1:15721",
        "OPENAI_TARGET_API_URL": "http://127.0.0.1:15721/v1",
        "HEADROOM_OFFLINE": "1",
        "HEADROOM_COMPRESS_USER_MESSAGES": "1",
        "HEADROOM_PROTECT_READS": "1",
        "HEADROOM_ACCURACY_GUARD": "strict",
        "HEADROOM_SAVINGS_PROFILE": "coding",
    }
    bad = {k: (env.get(k), v) for k, v in need.items() if str(env.get(k)) != v}
    rec("PASS" if not bad else "FAIL", "manifest key env (%d vars)" % len(env),
        "all correct" if not bad else "MISMATCH %s" % bad)
    tg = M.get("targets", None)
    rec("PASS" if tg in ([], None) else "FAIL", "manifest targets must stay empty",
        repr(tg) + " (non-empty = headroom would bypass cc-switch)")
else:
    rec("FAIL", "manifest exists", man + " MISSING")

print()
print("=" * 100)
print("B. agent wiring")
print("=" * 100)
cs = os.path.join(HOME, ".claude", "settings.json")
try:
    with open(cs, encoding="utf-8") as f:
        CJ = json.load(f)
    bu = (CJ.get("env") or {}).get("ANTHROPIC_BASE_URL", "")
    tok = (CJ.get("env") or {}).get("ANTHROPIC_AUTH_TOKEN", "")
    # cc-switch may legitimately put Claude in direct mode on another provider.
    # That is the user's choice, not a fault -- report it, never "fix" it.
    mode = attached = None
    try:
        with open(os.path.join(HOME, ".cc-switch", "live-state.json"), encoding="utf-8") as f:
            a = (json.load(f).get("apps") or {}).get("claude") or {}
        mode, attached = a.get("mode"), bool(a.get("attached"))
    except Exception:
        pass
    if "8787" in bu:
        rec("PASS", "claude ANTHROPIC_BASE_URL", bu)
    elif mode == "proxy" and attached:
        rec("FAIL", "claude ANTHROPIC_BASE_URL", bu + " (cc-switch proxy mode -> should be 8787)")
    else:
        rec("INFO", "claude not via headroom (user chose direct)",
            "%s  cc-switch mode=%s attached=%s" % (bu, mode, attached))
    # never print a credential
    shown = "PROXY_MANAGED" if tok == "PROXY_MANAGED" else (
        "<real key, %d chars, redacted>" % len(tok) if tok else "<empty>")
    rec("PASS" if tok == "PROXY_MANAGED" else "INFO",
        "claude auth token", shown)
except Exception as e:
    rec("FAIL", "claude settings.json parse", "%s: %s" % (type(e).__name__, e))

ct = os.path.join(HOME, ".codex", "config.toml")
try:
    with open(ct, encoding="utf-8") as f:
        CTXT = f.read()
    m = re.search(r'base_url\s*=\s*"([^"]+)"', CTXT)
    bu2 = m.group(1) if m else "(none)"
    rec("PASS" if "8787" in bu2 else "FAIL", "codex base_url", bu2)
    mm = re.search(r'^model\s*=\s*"([^"]+)"', CTXT, re.M)
    mw = re.search(r'wire_api\s*=\s*"([^"]+)"', CTXT)
    rec("PASS", "codex model / wire_api", "%s / %s" % (mm.group(1) if mm else "?", mw.group(1) if mw else "?"))
except Exception as e:
    rec("FAIL", "codex config.toml read", "%s: %s" % (type(e).__name__, e))

print()
print("=" * 100)
print("C. default window + skill roots")
print("=" * 100)
want = {"headroom", "skill-router"}
if os.path.isdir(ACTIVE):
    dirs = sorted(n for n in os.listdir(ACTIVE) if os.path.isdir(os.path.join(ACTIVE, n)))
    files = sorted(n for n in os.listdir(ACTIVE) if not os.path.isdir(os.path.join(ACTIVE, n)))
    good = set(dirs) == want and all(
        os.path.isfile(os.path.join(ACTIVE, d, "SKILL.md")) for d in dirs)
    rec("PASS" if good else "FAIL", "Skills-active == {headroom, skill-router}",
        "%s readable=%s" % (dirs, [os.path.isfile(os.path.join(ACTIVE, d, "SKILL.md")) for d in dirs]))
    rec("PASS", "Skills-active non-dir entries (app state, kept)", str(files) or "(none)")
else:
    rec("FAIL", "Skills-active exists", ACTIVE + " MISSING")

ROOTS = [
    ("claude", os.path.join(HOME, ".claude", "skills")),
    ("agents(DSH)", os.path.join(HOME, ".agents", "skills")),
    ("opencode", os.path.join(HOME, ".config", "opencode", "skills")),
    ("workbuddy", os.path.join(HOME, ".workbuddy", "skills")),
    ("workbuddy-ai", os.path.join(HOME, ".workbuddy-ai", "skills")),
    ("openclaw", os.path.join(HOME, ".openclaw", "skills")),
    ("codex", os.path.join(HOME, ".codex", "skills")),
    ("qoder", os.path.join(HOME, ".qoder", "skills")),
    ("qoder-cn", os.path.join(HOME, ".qoder-cn", "skills")),
    ("herdsman", os.path.join(HOME, ".herdsman", "work", "skills")),
    ("dsh", os.path.join(HOME, ".dsh", "skills")),
    ("cc-switch", os.path.join(HOME, ".cc-switch", "skills")),
]
for label, root in ROOTS:
    if not os.path.isdir(root):
        rec("FAIL", "root %s" % label, root + " MISSING/unreadable")
        continue
    kids = [n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))]
    have = [d for d in want if os.path.isfile(os.path.join(root, d, "SKILL.md"))]
    rp = reparse(root)
    kind = ("junction->" + target(root)) if rp else "realdir"
    rec("PASS" if set(have) == want else "FAIL", "root %s has both" % label,
        "%d dirs, both=%s, %s" % (len(kids), set(have) == want, kind[:70]))

print()
print("=" * 100)
print("D. library integrity")
print("=" * 100)
libdirs = sorted(n for n in os.listdir(LIB)
                 if os.path.isdir(os.path.join(LIB, n)) and not n.startswith("."))
bad_fm, mismatch, nodesc = [], [], []
KNOWN_EXC = {"reverse-trace": "spider-king", "reverse-wechat-miniapp": "wechat-miniapp-reverse",
             "web-kimi": "webapp-building", "brave-web-search": "web-search",
             "sickn33-frontend-slides": "frontend-slides",
             "barry-liu-888-requirement-translator": "requirement-translator",
             "barnhardt-enterprises-inc-checkpoint": "checkpoint"}
for d in libdirs:
    sm = os.path.join(LIB, d, "SKILL.md")
    if not os.path.isfile(sm):
        bad_fm.append(d + " (no SKILL.md)")
        continue
    n, ds = fm(sm)
    if not n:
        bad_fm.append(d + " (no name)")
    if not ds:
        nodesc.append(d)
    if n and n != d and KNOWN_EXC.get(d) != n:
        mismatch.append("%s -> %s" % (d, n))
rec("PASS" if not bad_fm else "FAIL", "library %d skills, SKILL.md+name" % len(libdirs),
    "all valid" if not bad_fm else str(bad_fm))
rec("PASS" if not nodesc else "WARN", "every skill has description", "all" if not nodesc else str(nodesc))
rec("PASS" if not mismatch else "WARN", "dir name == frontmatter name",
    "all (known exceptions allowed)" if not mismatch else str(mismatch))
rec("PASS" if os.path.isdir(DISABLED) else "FAIL", "Skills-disabled exists",
    "%d parked" % len(os.listdir(DISABLED)) if os.path.isdir(DISABLED) else "MISSING")

print()
print("=" * 100)
print("E. QoderToolkit junction + hardcoded paths inside its SKILL.md")
print("=" * 100)
rp = reparse(QTK)
rec("PASS" if rp and os.path.isdir(QTK) else "FAIL", "D:\\QoderToolkit junction resolves",
    "%s -> %s" % (bool(rp), target(QTK)))
qsm = os.path.join(QTK, "qoder-toolkit", "SKILL.md")
if os.path.isfile(qsm):
    with open(qsm, encoding="utf-8", errors="replace") as f:
        qt = f.read()
    refs = sorted(set(re.findall(r"D:\\QoderToolkit[\\\w\-.]*", qt)))
    missing = [r for r in refs if not os.path.exists(r)]
    rec("PASS" if not missing else "FAIL", "qoder-toolkit hardcoded paths resolve",
        "%d refs, missing=%s" % (len(refs), missing or "none"))
else:
    rec("FAIL", "qoder-toolkit SKILL.md", qsm + " MISSING")
qdirs = sorted(n for n in os.listdir(QTK)
               if os.path.isdir(os.path.join(QTK, n)) and not n.startswith(".")) if os.path.isdir(QTK) else []
qbad = [d for d in qdirs if not os.path.isfile(os.path.join(QTK, d, "SKILL.md"))]
rec("PASS" if not qbad else "FAIL", "QoderToolkit %d skills valid" % len(qdirs), str(qbad or "all"))

print()
print("=" * 100)
print("F. router catalog + scripts")
print("=" * 100)
cat = os.path.join(ROUTER, "catalog.json")
if os.path.isfile(cat):
    with open(cat, encoding="utf-8") as f:
        C = json.load(f)
    entries = C.get("skills", C) if isinstance(C, dict) else C
    n_cat = len(entries)
    cat_mtime = os.path.getmtime(cat)
    newest = max(os.path.getmtime(os.path.join(LIB, d)) for d in libdirs)
    stale = newest > cat_mtime + 5
    rec("WARN" if stale else "PASS", "catalog fresh vs library",
        "%d entries; library newer by %.0fs" % (n_cat, newest - cat_mtime) if stale
        else "%d entries, up to date" % n_cat)
else:
    rec("FAIL", "catalog.json", "MISSING")

for f_ in ["router.py", "ops.py", "wire_agents.py", "wire_headroom.py",
           "ccswitch_policy.py", "seed_kompress.py", "SKILL.md"]:
    p = os.path.join(ROUTER, f_)
    rec("PASS" if os.path.isfile(p) else "FAIL", "file %s" % f_,
        "%d B" % os.path.getsize(p) if os.path.isfile(p) else "MISSING")

# stale absolute references to the pre-reorg G:\AIrenwu layout
stale_refs = {}
for f_ in os.listdir(ROUTER):
    if not f_.endswith((".py", ".md")):
        continue
    p = os.path.join(ROUTER, f_)
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        continue
    hits = set(re.findall(r"G:\\AIrenwu\\(?:_scan|_backup)[\\\w\-.]*", txt))
    dead = sorted(h for h in hits if not os.path.exists(h))
    if dead:
        stale_refs[f_] = dead
rec("PASS" if not stale_refs else "WARN", "no stale G:\\AIrenwu\\_scan|_backup refs",
    "clean" if not stale_refs else json.dumps(stale_refs, ensure_ascii=False)[:400])

print()
print("=" * 100)
print("G. cc-switch policy DB")
print("=" * 100)
db = os.path.join(HOME, ".cc-switch", "cc-switch.db")
tmp = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "audit_cc.db")
try:
    shutil.copy2(db, tmp)
    con = sqlite3.connect(tmp)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(skills)")
    cols = [r[1] for r in cur.fetchall()]
    en = [c for c in cols if c.startswith("enabled_")]
    cur.execute("SELECT id, %s FROM skills" % ", ".join(en))
    rows = cur.fetchall()
    on_all, off_all, mixed = [], [], []
    for r in rows:
        vals = r[1:]
        if all(vals):
            on_all.append(r[0])
        elif not any(vals):
            off_all.append(r[0])
        else:
            mixed.append((r[0], sum(vals)))
    con.close()
    good = set(on_all) == {"local:headroom", "local:skill-router"} and not mixed
    rec("PASS" if good else "FAIL", "cc-switch: only 2 skills enabled",
        "%d switch cols; ON=%s; OFF=%d; MIXED=%s" % (len(en), on_all, len(off_all), mixed))
except Exception as e:
    rec("FAIL", "cc-switch DB read", "%s: %s" % (type(e).__name__, e))

print()
print("=" * 100)
print("H. autostart + Kompress model cache + models.json")
print("=" * 100)
vbs = os.path.join(HOME, "AppData", "Roaming", "Microsoft", "Windows",
                   "Start Menu", "Programs", "Startup", "headroom-autostart.vbs")
rec("PASS" if os.path.isfile(vbs) else "FAIL", "Startup autostart entry",
    "%d B" % os.path.getsize(vbs) if os.path.isfile(vbs) else "MISSING")
ens = os.path.join(HOME, ".headroom", "deploy", "default", "ensure-headroom.ps1")
rec("PASS" if os.path.isfile(ens) else "FAIL", "ensure-headroom.ps1 exists", str(os.path.isfile(ens)))
try:
    out = subprocess.run(["schtasks", "/query", "/tn", "headroom-default-health", "/fo", "LIST"],
                         capture_output=True, text=True, timeout=30)
    txt = (out.stdout or "") + (out.stderr or "")
    ok = out.returncode == 0 and "headroom-default-health" in txt
    rec("PASS" if ok else "WARN", "health scheduled task registered",
        "found" if ok else txt.strip().replace("\n", " ")[:160])
except Exception as e:
    rec("WARN", "health scheduled task query", "%s" % e)

onnx = os.path.join(HFHUB, "models--chopratejas--kompress-v2-base", "snapshots",
                    "b1563631b35bfdcee37587ad530147497d820d4c", "onnx", "kompress-int8-wo.onnx")
if os.path.isfile(onnx):
    sz = os.path.getsize(onnx)
    rec("PASS" if sz > 250_000_000 else "FAIL", "Kompress ONNX cached", "%.1f MB" % (sz / 1e6))
else:
    rec("FAIL", "Kompress ONNX cached", onnx + " MISSING (ML compressor would silently degrade)")
tokdir = os.path.join(HFHUB, "models--answerdotai--ModernBERT-base", "snapshots",
                      "8949b909ec900327062f0ebf497f51aef5e6f0c8")
rec("PASS" if os.path.isdir(tokdir) else "FAIL", "ModernBERT tokenizer cached", str(os.path.isdir(tokdir)))

mj = os.path.join(HOME, ".headroom", "models.json")
if os.path.isfile(mj):
    try:
        with open(mj, encoding="utf-8") as f:
            MJ = json.load(f)
        n = sum(len(v.get("context_limits", {})) for v in MJ.values() if isinstance(v, dict))
        rec("PASS" if n else "WARN", "models.json parses", "%d model limits" % n)
    except Exception as e:
        rec("FAIL", "models.json parses", "%s" % e)
else:
    rec("WARN", "models.json", "MISSING (falls back to conservative 128k)")

print()
print("=" * 100)
print("I. recent log anomalies (headroom + cc-switch)")
print("=" * 100)
PATTERNS = [
    ("headroom ERROR/Traceback", HRLOG, r"\bERROR\b|Traceback|CRITICAL"),
    ("headroom Kompress failure", HRLOG, r"Kompress.*(failed|requires onnxruntime|not cached)"),
    ("cc-switch balance/circuit", CCLOG, r"Insufficient account balance|所有供应商.*熔断"),
]
for label, path, pat in PATTERNS:
    if not os.path.isfile(path):
        rec("WARN", label, "log missing: " + path)
        continue
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    tail = lines[-4000:]
    hits = [l.rstrip() for l in tail if re.search(pat, l)]
    rec("PASS" if not hits else "WARN", label,
        "none in last %d lines" % len(tail) if not hits
        else "%d hits, last: %s" % (len(hits), hits[-1][:170]))
if os.path.isfile(HRLOG):
    with open(HRLOG, encoding="utf-8", errors="replace") as f:
        alltxt = f.read()
    loaded = "Kompress ONNX loaded" in alltxt
    rec("PASS" if loaded else "FAIL", "Kompress has loaded at least once", str(loaded))

print()
print("=" * 100)
print("J. zero-byte config scan (phase-1 WorkBuddy corruption class)")
print("=" * 100)
for label, root in [("workbuddy", os.path.join(HOME, ".workbuddy")),
                    ("workbuddy-ai", os.path.join(HOME, ".workbuddy-ai"))]:
    zeros, total = [], 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in ("node_modules", ".git")]
        for fn in fns:
            if not fn.endswith(".json"):
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) == 0:
                    zeros.append(os.path.relpath(p, root))
                    continue
                with open(p, "rb") as fh:
                    if not fh.read(4096).strip(b"\x00"):
                        zeros.append(os.path.relpath(p, root))
                total += 1
            except OSError:
                pass
    rec("PASS" if not zeros else "WARN", "%s all-zero/empty JSON" % label,
        "%d/%d clean" % (total, total) if not zeros else "%d bad: %s" % (len(zeros), zeros[:6]))

print()
print("=" * 100)
print("K. disk space + backups")
print("=" * 100)
for drv in ("C:\\", "D:\\", "G:\\"):
    try:
        u = shutil.disk_usage(drv)
        pct = u.free / u.total * 100
        rec("PASS" if pct > 8 else "WARN", "free space %s" % drv,
            "%.1f GB free (%.1f%%)" % (u.free / 1e9, pct))
    except OSError as e:
        rec("WARN", "free space %s" % drv, str(e))
for cand in [r"G:\AIrenwu\03_备份", r"G:\AIrenwu\_backup"]:
    if os.path.isdir(cand):
        n = sum(len(f) for _, _, f in os.walk(cand))
        rec("PASS", "backups at %s" % cand, "%d files" % n)
        break
else:
    rec("WARN", "backup directory", "not found at either known location")

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)
for lv in ("FAIL", "WARN", "INFO", "PASS"):
    items = [r for r in RESULTS if r[0] == lv]
    print("%s: %d" % (lv, len(items)))
    if lv != "PASS":
        for _, n, d in items:
            print("   - %s :: %s" % (n, d[:190]))
