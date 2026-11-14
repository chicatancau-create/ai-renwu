# -*- coding: utf-8 -*-
"""快速确认两个仓库根目录存在并列出顶层结构（只读，不改动源仓库）。"""
import os, sys

ROOTS = [
    r"E:\OBsidian\全栈工程师学习资料库",
    r"G:\CodeWeave",
]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for root in ROOTS:
    print("=" * 60)
    print("ROOT:", root)
    if not os.path.isdir(root):
        print("  !! 不存在或不是目录")
        continue
    entries = sorted(os.listdir(root))
    dirs = [e for e in entries if os.path.isdir(os.path.join(root, e))]
    files = [e for e in entries if not os.path.isdir(os.path.join(root, e))]
    print(f"  顶层目录 {len(dirs)} 个, 顶层文件 {len(files)} 个")
    for d in dirs:
        print("  [D]", d)
    for f in files:
        try:
            size = os.path.getsize(os.path.join(root, f))
        except OSError:
            size = -1
        print(f"  [F] {f}  ({size} bytes)")
