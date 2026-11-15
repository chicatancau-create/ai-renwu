# -*- coding: utf-8 -*-
"""Search the Recycle Bins for the wiped skill-router / headroom files."""
import os
import time

WANT = {"router.py", "ops.py", "wire_guard.py", "wire_headroom.py", "SKILL.md",
        "catalog.json", "CATALOG.md", "wire_agents.py", "ccswitch_policy.py",
        "seed_kompress.py"}
hits = []
for base in ["D:\\$RECYCLE.BIN", "C:\\$Recycle.Bin", "G:\\$RECYCLE.BIN"]:
    if not os.path.isdir(base):
        continue
    for dp, dns, fns in os.walk(base):
        for fn in fns:
            if fn in WANT or fn.startswith("$R") and fn.endswith((".py", ".md", ".json")):
                p = os.path.join(dp, fn)
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    continue
                if sz < 400:
                    continue
                # peek at the first line to identify skill files
                head = ""
                try:
                    with open(p, encoding="utf-8", errors="replace") as f:
                        head = f.readline().rstrip()[:90]
                except OSError:
                    pass
                hits.append((os.path.getmtime(p), sz, p, head))

print("candidates in recycle bins: %d" % len(hits))
for mt, sz, p, head in sorted(hits, reverse=True)[:60]:
    print("  %s %8dB %-70s | %s" % (
        time.strftime("%m-%d %H:%M:%S", time.localtime(mt)), sz, p[-70:], head))

print()
print("=== also: what survived in the pathfix backup dir ===")
b = "G:\\AIrenwu\\03_\u5907\u4efd\\_backup\\script-pathfix"
if os.path.isdir(b):
    for dp, dns, fns in os.walk(b):
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            print("  %8dB  %s" % (os.path.getsize(p), p))

print()
print("=== upstream headroom SKILL.md copies ===")
u = "G:\\AIrenwu\\05_\u53d6\u8bc1\u626b\u63cf\\_scan\\headroom_upstream"
if os.path.isdir(u):
    for fn in sorted(os.listdir(u)):
        p = os.path.join(u, fn)
        print("  %8dB  %s" % (os.path.getsize(p), fn))
