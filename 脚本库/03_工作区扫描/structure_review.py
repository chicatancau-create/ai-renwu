# -*- coding: utf-8 -*-
r"""结构审查：浅层树+任务归档分层合规+手册全树+脚本库分类核对。只读。
用法: <python绝对路径> -X utf8 structure_review.py [OUTDIR]
  OUTDIR 须含 inventory.py 生成的 filelist.csv（默认当前目录），review.txt 也写到这里。"""
import os, sys, io, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()

rows = list(csv.DictReader(open(os.path.join(OUT, "filelist.csv"), encoding="utf-8-sig")))
paths = [r["relpath"] for r in rows]

def human(n):
    n = float(n)
    for u in ["B","KB","MB","GB"]:
        if n < 1024 or u == "GB":
            return f"{n:.1f}{u}" if u != "B" else f"{int(n)}B"
        n /= 1024

agg = {}
for r in rows:
    parts = r["relpath"].split("\\")
    for i in range(1, len(parts)):
        k = "\\".join(parts[:i])
        a = agg.setdefault(k, [0,0]); a[0]+=1; a[1]+=int(r["bytes"])

lines = []
lines.append("== 浅层树（深度<=3，01_任务归档 只列到任务名）==")
keys = sorted(agg.keys(), key=str.lower)
for k in keys:
    depth = k.count("\\") + 1
    if depth > 3: continue
    if k.startswith("01_任务归档\\") and depth >= 3: continue
    if k.startswith(".git"): continue
    c,b = agg[k]
    lines.append(f"{'  '*(depth-1)}{k.split(chr(92))[-1]}/  ({c}文件 {human(b)})")
# 根散件
for r in rows:
    if "\\" not in r["relpath"]:
        lines.append(f"  [根散件] {r['relpath']} ({human(r['bytes'])})")

lines.append("")
lines.append("== 01_任务归档 分层合规（标准: 01_报告/02_证据日志/03_工具脚本/04_产物）==")
tasks = sorted({p.split("\\")[1] for p in paths if p.startswith("01_任务归档\\")}, key=str.lower)
STD = {"01_报告","02_证据日志","03_工具脚本","04_产物"}
for t in tasks:
    prefix = f"01_任务归档\\{t}\\"
    sub = {p[len(prefix):].split("\\")[0] for p in paths if p.startswith(prefix)}
    direct = [p[len(prefix):] for p in paths if p.startswith(prefix) and "\\" not in p[len(prefix):]]
    missing = STD - sub
    extra = sub - STD
    flag = []
    if missing: flag.append("缺:" + ",".join(sorted(missing)))
    if extra: flag.append("非标准子目录:" + ",".join(sorted(extra)))
    if direct: flag.append("任务根散件:" + ",".join(direct[:8]) + ("..." if len(direct)>8 else ""))
    c,b = agg.get(f"01_任务归档\\{t}",[0,0])
    lines.append(f"  {t}  ({c}文件 {human(b)})  {'; '.join(flag) if flag else 'OK'}")

lines.append("")
lines.append("== 本地AI使用手册 全树 ==")
hb = sorted([p for p in paths if p.startswith("本地AI使用手册\\")], key=str.lower)
for p in hb:
    r = next(x for x in rows if x["relpath"]==p)
    lines.append(f"  {p[len('本地AI使用手册')+1:]}  ({human(r['bytes'])})")

lines.append("")
lines.append("== 02_项目代码 / 03_备份 / 04_磁盘与系统 / 05_取证扫描 全树 ==")
for top in ["02_项目代码","03_备份","04_磁盘与系统","05_取证扫描"]:
    for p in sorted([x for x in paths if x.startswith(top+"\\")], key=str.lower):
        r = next(x for x in rows if x["relpath"]==p)
        lines.append(f"  {p}  ({human(r['bytes'])})")

txt = "\n".join(lines)
open(os.path.join(OUT,"review.txt"),"w",encoding="utf-8").write(txt)
print(f"review.txt {len(lines)}行 已写入")
