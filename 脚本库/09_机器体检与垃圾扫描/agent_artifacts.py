# -*- coding: utf-8 -*-
"""盘点各 AI Agent 与本机工具留下的产物：大小 / 文件数 / 最近写入 / 静默天数 / 处置档位。

用法：
  python agent_artifacts.py                 # 全部点位
  python agent_artifacts.py --json          # 机器可读
  python agent_artifacts.py --days 7        # 只看静默超过 7 天的

本脚本**不删除任何东西**。删除要同时满足两条才允许动手：
①内容可证明为无（0 字节 / 全零 / 指向的路径已消失）**且**②位置属于可丢弃层（TEMP、缓存、日志轮替）。
落在 workspace|sessions|profiles|data|AppData\\Roaming\\<app> 这类应用状态层的，一律只报告。
本机 DisableLastAccess=1，所以 atime 证明不了「有没有被重读」，只能看 mtime。
"""
import argparse
import json
import os
import sys
import time

LA = os.environ.get("LOCALAPPDATA", "")
UP = os.environ.get("USERPROFILE", "")
ROAM = os.environ.get("APPDATA", "")

SPOTS = [
    ("会话产物", "Qoder 临时(TEMP)", os.path.join(LA, "Temp"), "安全"),
    ("会话产物", "Qoder tmp", os.path.join(UP, ".qoder", "tmp"), "需确认"),
    ("会话产物", "Qoder shell-snapshots", os.path.join(UP, ".qoder", "shell-snapshots"), "安全"),
    ("会话产物", "Qoder logs", os.path.join(UP, ".qoder", "logs"), "安全"),
    ("会话产物", "Qoder file-history", os.path.join(UP, ".qoder", "file-history"), "需确认"),
    ("会话产物", "Qoder 国内版", os.path.join(UP, ".qoder-cn"), "需确认"),
    ("应用状态", "WorkBuddy", os.path.join(UP, ".workbuddy-ai"), "禁区"),
    ("应用状态", "DSH", os.path.join(UP, ".dsh"), "禁区"),
    ("会话产物", "Codex", os.path.join(UP, ".codex"), "需确认"),
    ("会话产物", "Claude", os.path.join(UP, ".claude"), "需确认"),
    ("会话产物", "Gemini", os.path.join(UP, ".gemini"), "需确认"),
    ("缓存", "npm-cache", os.path.join(LA, "npm-cache"), "安全"),
    ("缓存", "pnpm store", os.path.join(LA, "pnpm", "store"), "安全"),
    ("缓存", "pip", os.path.join(LA, "pip", "Cache"), "安全"),
    ("缓存", "uv/huggingface", "D:/uv/data", "安全"),
    ("缓存", "通用 .cache", os.path.join(UP, ".cache"), "需确认"),
    ("工具状态", "AI-Tool-State", "D:/AI-Tool-State", "禁区"),
    ("回收站", "各盘 $RECYCLE.BIN", None, "需确认"),
]


def measure(path):
    size = count = 0
    newest = 0.0
    unreadable = 0
    try:
        entries = list(os.scandir(path))
    except OSError:
        return None
    stack = [path]
    while stack:
        cur = stack.pop()
        try:
            for e in os.scandir(cur):
                try:
                    if e.is_symlink():
                        continue
                    if e.is_dir(follow_symlinks=False):
                        stack.append(e.path)
                    else:
                        st = e.stat(follow_symlinks=False)
                        size += st.st_size
                        count += 1
                        newest = max(newest, st.st_mtime)
                except OSError:
                    unreadable += 1
        except OSError:
            unreadable += 1
    return {"bytes": size, "files": count, "newest": newest, "unreadable": unreadable}


def recycle_bins():
    rows = []
    for d in "CDEFGHIJKL":
        p = "%s:/$RECYCLE.BIN" % d
        if os.path.isdir(p):
            rows.append(("%s 回收站" % d, p))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--days", type=float, default=0, help="只显示静默超过 N 天的条目")
    args = ap.parse_args()

    now = time.time()
    out = []
    for kind, name, path, grade in SPOTS:
        paths = recycle_bins() if path is None else [(name, path)]
        for nm, p in paths:
            if not os.path.isdir(p):
                out.append({"kind": kind, "name": nm, "path": p, "state": "不存在或读不了", "grade": grade})
                continue
            m = measure(p)
            if m is None:
                out.append({"kind": kind, "name": nm, "path": p, "state": "读不了(需提权)", "grade": grade})
                continue
            idle = (now - m["newest"]) / 86400.0 if m["newest"] else None
            out.append({
                "kind": kind, "name": nm, "path": p, "grade": grade,
                "gib": round(m["bytes"] / 2 ** 30, 3), "files": m["files"],
                "idle_days": round(idle, 1) if idle is not None else None,
                "newest": time.strftime("%Y-%m-%d %H:%M", time.localtime(m["newest"])) if m["newest"] else "-",
                "unreadable": m["unreadable"],
                "state": "空" if m["files"] == 0 else "有内容",
            })
    out.sort(key=lambda r: -r.get("gib", -1))
    if args.days:
        out = [r for r in out if (r.get("idle_days") or 0) >= args.days]

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    print("%-10s %-22s %8s %7s %9s %-16s %-6s %s" % ("层", "点位", "GiB", "文件", "静默天", "最近写入", "档位", "路径"))
    for r in out:
        if "gib" not in r:
            print("%-10s %-22s %8s %7s %9s %-16s %-6s %s" %
                  (r["kind"], r["name"], "-", "-", "-", r["state"], r["grade"], r["path"]))
            continue
        print("%-10s %-22s %8.2f %7d %9s %-16s %-6s %s" %
              (r["kind"], r["name"], r["gib"], r["files"], r["idle_days"], r["newest"], r["grade"], r["path"]))
    print("\n档位说明：安全=缓存/日志轮替，删了能重建；需确认=可能有会话还在用；禁区=应用状态层，只报告。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
