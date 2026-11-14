# -*- coding: utf-8 -*-
"""只读核验：.workbuddy 是否被 git 跟踪；跟踪 md 的构成。git ls-files 只读，不写 index。"""
import sys, subprocess, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"E:\OBsidian\全栈工程师学习资料库"
r = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], capture_output=True, timeout=120)
files = [x.decode("utf-8", "replace") for x in r.stdout.split(b"\0") if x]
print("tracked total:", len(files))
wb = [f for f in files if f.startswith(".workbuddy")]
print("tracked .workbuddy:", len(wb))
for f in wb:
    print("  ", f)
md = [f for f in files if f.lower().endswith(".md")]
print("tracked md:", len(md))
top = collections.Counter(f.split("/")[0] for f in md)
for k, v in sorted(top.items()):
    print("  md by top:", k, v)
gi = [f for f in files if f.startswith("05-外部资料库/")]
print("tracked under 05:", len(gi))
for f in gi[:12]:
    print("  ", f)
