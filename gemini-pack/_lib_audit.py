# -*- coding: utf-8 -*-
"""审计 02-资料库-快照.md 各节字节数，指导体积裁剪（只读）。"""
import sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"G:\AIrenwu\gemini-pack\02-资料库-快照.md"
t = open(p, encoding="utf-8").read()
b = lambda s: len(s.encode("utf-8"))
print("TOTAL bytes:", b(t), " lines:", len(t.splitlines()))
parts = re.split(r"(?m)^(## .+)$", t)
print("HEADER(before first ##):", b(parts[0]))
for i in range(1, len(parts), 2):
    head, body = parts[i], parts[i + 1]
    size = b(head) + b(body)
    print("%6d  %s" % (size, head[:70]))
    if size > 7000:
        sub = re.split(r"(?m)^(### .+)$", body)
        print("        pre-###:", b(sub[0]))
        for j in range(1, len(sub), 2):
            print("        %6d  %s" % (b(sub[j]) + b(sub[j + 1]), sub[j][:64]))
