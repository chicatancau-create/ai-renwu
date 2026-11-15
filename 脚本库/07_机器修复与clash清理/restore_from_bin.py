# -*- coding: utf-8 -*-
"""Parse Recycle Bin $I metadata to prove WHAT was deleted, WHEN, and from WHERE,
then restore everything that belonged to the skill library / default window.

$I file layout (Win10+ v2):
  0..7   header (2)
  8..15  original size (int64)
 16..23  deletion time (FILETIME, UTC)
 24..27  path length in chars (uint32)   [v2 only]
 28..    original full path, UTF-16LE, NUL-terminated
"""
import datetime
import os
import shutil
import struct
import sys

APPLY = "--apply" in sys.argv
PREFIXES = ("D:\\Skills\\headroom", "D:\\Skills\\skill-router", "D:\\Skills-active")
BINS = ["D:\\$RECYCLE.BIN", "C:\\$Recycle.Bin", "G:\\$RECYCLE.BIN"]


def filetime(v):
    if v == 0:
        return None
    return datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=v / 10)


rows = []
for b in BINS:
    if not os.path.isdir(b):
        continue
    for sid in os.listdir(b):
        d = os.path.join(b, sid)
        if not os.path.isdir(d):
            continue
        try:
            entries = os.listdir(d)
        except OSError:
            continue          # other users' / SYSTEM's bin: not ours to read
        for fn in entries:
            if not fn.startswith("$I"):
                continue
            ip = os.path.join(d, fn)
            try:
                with open(ip, "rb") as f:
                    raw = f.read()
            except OSError:
                continue
            if len(raw) < 28:
                continue
            hdr, size, ft = struct.unpack("<qqq", raw[:24])
            if hdr == 2:
                (plen,) = struct.unpack("<I", raw[24:28])
                path = raw[28:28 + plen * 2].decode("utf-16-le", "replace").rstrip("\x00")
            else:
                path = raw[24:24 + 520].decode("utf-16-le", "replace").rstrip("\x00")
            if not path.startswith(PREFIXES):
                continue
            rp = os.path.join(d, "$R" + fn[2:])
            rows.append({
                "orig": path,
                "data": rp,
                "size": size,
                "deleted": filetime(ft),
                "exists": os.path.exists(rp),
                "isdir": os.path.isdir(rp),
            })

rows.sort(key=lambda r: (r["deleted"] or datetime.datetime.min))
print("recycled entries belonging to the skill library / default window: %d" % len(rows))
print()
dts = sorted({r["deleted"] for r in rows if r["deleted"]})
if dts:
    print("deletion timestamps (UTC): %s .. %s" % (dts[0], dts[-1]))
    print("deletion timestamps (local): %s .. %s" % (
        dts[0] + datetime.timedelta(hours=8), dts[-1] + datetime.timedelta(hours=8)))
print()
for r in rows:
    print("  %s  %9dB  %-58s  data=%s%s" % (
        (r["deleted"] + datetime.timedelta(hours=8)).strftime("%m-%d %H:%M:%S") if r["deleted"] else "?",
        r["size"], r["orig"], "OK" if r["exists"] else "MISSING",
        " (dir)" if r["isdir"] else ""))

if not APPLY:
    print()
    print("(report only; rerun with --apply to restore)")
    sys.exit(0)

print()
print("=== restoring ===")
ok = fail = 0
# restore files first (deepest paths first so parents exist), skip directory entries
files = [r for r in rows if not r["isdir"] and r["exists"]]
files.sort(key=lambda r: -r["orig"].count("\\"))
for r in files:
    dst = r["orig"]
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            print("  SKIP (already present) %s" % dst)
            continue
        shutil.copy2(r["data"], dst)
        got = os.path.getsize(dst)
        if got != r["size"]:
            print("  SIZE MISMATCH %s (%d vs %d)" % (dst, got, r["size"]))
            fail += 1
        else:
            print("  restored %8dB  %s" % (got, dst))
            ok += 1
    except OSError as e:
        print("  FAIL %s : %s" % (dst, e))
        fail += 1
print()
print("restored=%d failed=%d" % (ok, fail))
