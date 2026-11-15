"""Prove the backup is actually restorable: clone from each remote into a scratch
dir and compare every tracked file's sha256 against the live library.
"push succeeded" is not evidence; byte-identical restore is.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(errors="replace")
GIT = r"D:\Git\cmd\git.exe"
SCRATCH = r"G:\AIrenwu\_audit\restore-test"
env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
CASES = [
    ("ai-skills", r"D:\Skills",
     ["https://github.com/chicatancau-create/ai-skills.git",
      "https://gitcode.com/zhoumoyukuai/ai-skills.git"]),
    ("qoder-toolkit", r"D:\QoderToolkit",
     ["https://github.com/chicatancau-create/qoder-toolkit.git",
      "https://gitcode.com/zhoumoyukuai/qoder-toolkit.git"]),
]


def rmtree(p):
    """git marks pack files read-only on Windows; plain rmtree silently leaves them
    (ignore_errors=True) and the next clone then fails with 'already exists'."""
    import stat

    def onerr(fn, path, exc):
        try:
            os.chmod(path, stat.S_IWRITE)
            fn(path)
        except OSError:
            pass
    if os.path.isdir(p):
        shutil.rmtree(p, onerror=onerr)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args, cwd=None, timeout=1800):
    r = subprocess.run([GIT] + args, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=env, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


os.makedirs(SCRATCH, exist_ok=True)
overall = True
for name, live, urls in CASES:
    rc, tracked, _ = run(["ls-files"], cwd=live)
    files = [f for f in tracked.splitlines() if f.strip()]
    print("\n=== %s : %d tracked files ===" % (name, len(files)), flush=True)
    for url in urls:
        host = "github" if "github" in url else "gitcode"
        dst = os.path.join(SCRATCH, name + "-" + host)
        if os.path.isdir(dst):
            rmtree(dst)
        t0 = time.time()
        rc, out, err = run(["clone", "--quiet", "--depth", "1", url, dst])
        dt = time.time() - t0
        if rc != 0:
            print("  %-8s CLONE FAILED rc=%d %s" % (host, rc, err[:200]), flush=True)
            overall = False
            continue
        same = diff = missing = 0
        bad = []
        for rel in files:
            a = os.path.join(live, rel.replace("/", os.sep))
            b = os.path.join(dst, rel.replace("/", os.sep))
            if not os.path.isfile(b):
                missing += 1
                bad.append("MISSING " + rel)
                continue
            if sha(a) == sha(b):
                same += 1
            else:
                diff += 1
                bad.append("DIFF " + rel)
        # excluded dirs must NOT be present in the clone
        EXC = {"ai-skills": ["docx", "pdf", "pptx", "xlsx", "reverse-trace",
                             "reverse-wechat-miniapp", "webapp-building"],
               "qoder-toolkit": ["web-kimi"]}[name]
        leaked = [d for d in EXC if os.path.isdir(os.path.join(dst, d))]
        print("  %-8s clone %.1fs | identical=%d diff=%d missing=%d | excluded-leaked=%s"
              % (host, dt, same, diff, missing, leaked or "none"), flush=True)
        for b in bad[:6]:
            print("      ", b, flush=True)
        if diff or missing or leaked:
            overall = False
        rmtree(dst)

print("\n=== VERDICT: %s ===" % ("ALL REMOTES RESTORE BYTE-IDENTICAL" if overall else "PROBLEM"),
      flush=True)
rmtree(SCRATCH)
