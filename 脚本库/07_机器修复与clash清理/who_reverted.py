"""Who reverted D:\\Skills\\skill-router\\router.py at 02:23:48?

Facts so far: an `edit` call reported success, the next python run said the file
did not exist, and now the file is back at the PRE-EDIT size/mtime (21053B,
02:10:43) which is byte-identical to the mirror copy.  shutil.copy2 preserves
mtime, so a restore-from-mirror is the prime suspect.  skill_shield.py itself
cannot overwrite a non-empty library file, so look for another actor.
"""
import os
import struct
import sys
import time

sys.stdout.reconfigure(errors="replace")


def tail(p, n=2600):
    if not os.path.isfile(p):
        return "(no file) " + p
    return open(p, encoding="utf-8", errors="replace").read()[-n:]


print("=== shield.log (fresh tail) ===")
print(tail(r"D:\AI-Tool-State\wire-guard\shield.log"))
print("\n=== guard.log (fresh tail) ===")
print(tail(r"D:\AI-Tool-State\wire-guard\guard.log", 1800))

print("\n=== recycle bin: anything deleted after 02:15 ? ===")
CUT = time.mktime(time.strptime("2026-11-15 02:15:00", "%Y-%m-%d %H:%M:%S"))
found = 0
for drive in ("C:", "D:", "E:", "G:"):
    base = drive + "\\$RECYCLE.BIN"
    if not os.path.isdir(base):
        continue
    try:
        sids = os.listdir(base)
    except OSError:
        continue
    for sid in sids:
        d = os.path.join(base, sid)
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for fn in names:
            if not fn.startswith("$I"):
                continue
            fp = os.path.join(d, fn)
            try:
                b = open(fp, "rb").read()
            except OSError:
                continue
            if len(b) < 28:
                continue
            try:
                hdr, size, ft = struct.unpack("<qqQ", b[:24])
                path = b[28:].decode("utf-16-le").rstrip("\x00") if hdr == 2 else b[24:].decode("utf-16-le").rstrip("\x00")
            except Exception:
                continue
            ts = ft / 10000000.0 - 11644473600.0
            if ts >= CUT:
                print("  %s  %9d  %s" % (time.strftime("%H:%M:%S", time.localtime(ts)), size, path))
                found += 1
print("recent deletions:", found)

print("\n=== mirror vs library byte compare ===")
import hashlib
for name in ("headroom", "skill-router"):
    for root in (r"D:\Skills", r"D:\Skills-mirror"):
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            fp = os.path.join(d, fn)
            if os.path.isfile(fp) and fn in ("router.py", "SKILL.md", "ops.py"):
                b = open(fp, "rb").read()
                print("  %-18s %-14s %-12s %8d  %s  %s" % (
                    root, name, fn, len(b),
                    hashlib.sha256(b).hexdigest()[:12],
                    time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(fp)))))

print("\n=== processes with a command line mentioning Skills / restore / unzip ===")
import subprocess
r = subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'Skills|shield|restore|Expand-Archive| unzip ' } | Select-Object ProcessId,Name,CommandLine | Format-List"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
print((r.stdout or "").strip()[:3000] or "(none)")
