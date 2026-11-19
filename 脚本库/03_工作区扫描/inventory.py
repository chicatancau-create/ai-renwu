# -*- coding: utf-8 -*-
r"""全量盘点 G:\AIrenwu：树状清单 + 统计 + 异常候选。只读，不改动任何文件。
输出 tree.txt / filelist.csv / summary.txt / anomalies.txt 到 OUTDIR。
用法: <python绝对路径> -X utf8 inventory.py [ROOT] [OUTDIR]
  ROOT 默认 G:\AIrenwu；OUTDIR 默认 当前目录\inventory_out。
  先跑本脚本生成 filelist.csv，再跑 structure_review.py [OUTDIR] 做结构审查。
"""
import os, sys, io, csv, hashlib, time
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else r"G:\AIrenwu"
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(os.getcwd(), "inventory_out")
LONG = "\\\\?\\" + ROOT
os.makedirs(OUT, exist_ok=True)

SKIP_ANY = {".git"}                      # 任何层级都跳过内部
COLLAPSE = {"node_modules", ".venv", "venv", "__pycache__"}  # 计数但树里不展开

files = []      # (relpath, size, mtime)
dirs = []       # (relpath, is_junction)
errors = []
junctions = []

def strip(p):
    r = p[len(LONG):] if p.startswith(LONG) else p
    return r[1:] if r.startswith("\\") else r

for cur, subdirs, fnames in os.walk(LONG, followlinks=False):
    rel = strip(cur)
    keep = []
    for d in sorted(subdirs):
        if d in SKIP_ANY:
            continue
        full = os.path.join(cur, d)
        try:
            st = os.lstat(full)
            if st.st_file_attributes & 0x400:  # REPARSE_POINT = junction/symlink
                junctions.append((strip(full), os.path.realpath(full)))
                dirs.append((strip(full), True))
                continue  # 不深入，避免环与重复计数
        except OSError as e:
            errors.append((strip(full), repr(e)))
        keep.append(d)
    subdirs[:] = keep
    if rel != "":
        dirs.append((rel, False))
    for f in sorted(fnames):
        full = os.path.join(cur, f)
        try:
            st = os.lstat(full)
            if st.st_file_attributes & 0x400:
                junctions.append((strip(full), os.path.realpath(full)))
                continue
            files.append((strip(full), st.st_size, st.st_mtime))
        except OSError as e:
            errors.append((strip(full), repr(e)))

files.sort(key=lambda x: x[0].lower())
dirs.sort(key=lambda x: x[0].lower())

with open(os.path.join(OUT, "filelist.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["relpath", "bytes", "mtime"])
    for p, s, m in files:
        w.writerow([p, s, datetime.fromtimestamp(m).strftime("%Y-%m-%d %H:%M:%S")])

agg = {}
for p, s, m in files:
    parts = p.split(os.sep)
    for i in range(1, len(parts)):
        key = os.sep.join(parts[:i])
        a = agg.setdefault(key, [0, 0])
        a[0] += 1; a[1] += s
top = {}
for p, s, m in files:
    t = p.split(os.sep)[0] if os.sep in p else "(根散件)"
    a = top.setdefault(t, [0, 0]); a[0] += 1; a[1] += s

def human(n):
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024 or u == "GB":
            return f"{n:.1f}{u}" if u != "B" else f"{int(n)}B"
        n /= 1024

children = {}
for p, s, m in files:
    parts = p.split(os.sep)
    parent = os.sep.join(parts[:-1])
    children.setdefault(parent, []).append(("F", parts[-1], s))
for d, j in dirs:
    parts = d.split(os.sep)
    parent = os.sep.join(parts[:-1])
    children.setdefault(parent, []).append(("D", parts[-1], -2 if j else -1))

lines = []
def emit(parent, prefix):
    entries = sorted(children.get(parent, []), key=lambda e: (e[0] != "D", e[1].lower()))
    for i, (kind, name, s) in enumerate(entries):
        last = i == len(entries) - 1
        branch = "└─ " if last else "├─ "
        if kind == "D":
            full = os.path.join(parent, name) if parent else name
            a = agg.get(full, [0, 0])
            if name in COLLAPSE:
                lines.append(f"{prefix}{branch}{name}/ [折叠不展开]  ({a[0]}文件 {human(a[1])})")
                continue
            tag = " [JUNCTION]" if s == -2 else ""
            lines.append(f"{prefix}{branch}{name}/{tag}  ({a[0]}文件 {human(a[1])})")
            emit(full, prefix + ("   " if last else "│  "))
        else:
            lines.append(f"{prefix}{branch}{name}  ({human(s)})")
emit("", "")
with open(os.path.join(OUT, "tree.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

sm = []
sm.append(f"盘点时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
sm.append(f"总文件数: {len(files)}  总大小: {human(sum(s for _, s, _ in files))}  目录数: {len(dirs)}")
sm.append("")
sm.append("顶层统计:")
for t, (c, b) in sorted(top.items(), key=lambda kv: -kv[1][1]):
    sm.append(f"  {t}: {c}文件 {human(b)}")
sm.append("")
sm.append("二层目录统计:")
for d, (c, b) in sorted(agg.items(), key=lambda kv: kv[0].lower()):
    if d.count(os.sep) == 1:
        sm.append(f"  {d}: {c}文件 {human(b)}")
with open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(sm))

an = []
an.append("== 根目录散件（大纲只许 README.md + .gitignore）==")
for p, s, m in files:
    if os.sep not in p and p not in ("README.md", ".gitignore"):
        an.append(f"  {p}  {human(s)}  mtime={datetime.fromtimestamp(m).strftime('%m-%d %H:%M:%S')}")
an.append("")
an.append("== 空目录 ==")
occupied = set()
for p, _, _ in files:
    parts = p.split(os.sep)
    for i in range(1, len(parts)):
        occupied.add(os.sep.join(parts[:i]))
for d, j in dirs:
    if d not in occupied and not j:
        an.append(f"  {d}")
an.append("")
an.append("== 大文件 (>20MB) ==")
for p, s, m in sorted(files, key=lambda x: -x[1]):
    if s > 20 * 1024 * 1024:
        an.append(f"  {human(s)}  {p}")
an.append("")
an.append("== 近24小时被写过的文件（并行会话活动线索）==")
now = time.time()
for p, s, m in sorted(files, key=lambda x: -x[2]):
    if now - m < 86400:
        an.append(f"  {datetime.fromtimestamp(m).strftime('%m-%d %H:%M')}  {human(s)}  {p}")
an.append("")
an.append("== Junction / 符号链接 ==")
for p, tgt in junctions:
    an.append(f"  {p} -> {tgt}")
an.append("")
an.append("== 读取错误 ==")
for p, e in errors[:50]:
    an.append(f"  {p}: {e}")
if len(errors) > 50:
    an.append(f"  ...另有 {len(errors)-50} 条")
an.append("")
an.append("== 疑似重复（同尺寸且 sha256 相同，<=5MB 文件）==")
bysize = {}
for p, s, m in files:
    if 0 < s <= 5 * 1024 * 1024:
        bysize.setdefault(s, []).append(p)
dupgroups = []
for s, ps in bysize.items():
    if len(ps) < 2:
        continue
    byhash = {}
    for p in ps:
        try:
            with open(os.path.join(LONG, p), "rb") as fh:
                h = hashlib.sha256(fh.read()).hexdigest()
            byhash.setdefault(h, []).append(p)
        except OSError as e:
            errors.append((p, repr(e)))
    for h, group in byhash.items():
        if len(group) > 1:
            dupgroups.append((s, group))
dupgroups.sort(key=lambda x: -x[0] * len(x[1]))
for s, group in dupgroups[:150]:
    an.append(f"  [{human(s)} x{len(group)}]")
    for p in group:
        an.append(f"      {p}")
if len(dupgroups) > 150:
    an.append(f"  ...另有 {len(dupgroups)-150} 组未列出")
with open(os.path.join(OUT, "anomalies.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(an))

print("\n".join(sm))
print(f"\n输出: {OUT}")
print(f"tree.txt {len(lines)}行 / anomalies.txt {len(an)}行 / 重复组 {len(dupgroups)} / 错误 {len(errors)}")
