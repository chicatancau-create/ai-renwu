# -*- coding: utf-8 -*-
"""扫描「尺寸正常但内容全 0x00」的文件（本机 NVMe 异常断电的典型后遗症）。

用法：
  python zero_fill_scan.py D:\\Models E:\\OpenHarmony        # 只读，阈值默认 1 MiB
  python zero_fill_scan.py C:\\ --min-mb 8 --limit 3000       # 只探前 3000 个候选，控制耗时
  python zero_fill_scan.py D:\\ --full                        # 对疑似文件逐字节确认（慢）

判定分三层，输出必须分开报：**全零 / 稀疏或占位 / 读不了**。
把「读不了」写成「不存在」是本机踩过的错（非提权令牌遇到拒绝访问会直接 False）。
"""
import argparse
import ctypes
import os
import sys

kernel32 = ctypes.windll.kernel32
GetCompressedFileSizeW = kernel32.GetCompressedFileSizeW
GetCompressedFileSizeW.restype = ctypes.c_uint32
GetCompressedFileSizeW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]


def real_allocated(path):
    hi = ctypes.c_uint32(0)
    lo = GetCompressedFileSizeW(path, ctypes.byref(hi))
    if lo == 0xFFFFFFFF and kernel32.GetLastError() != 0:
        return None
    return (hi.value << 32) | lo


def probe(path, chunk=1 << 20, full=False):
    """返回 'zero' / 'has-data' / 'unreadable'。"""
    try:
        size = os.path.getsize(path)
        if size == 0:
            return "zero"
        with open(path, "rb", 0) as fh:
            spans = [(0, chunk)] if size <= chunk * 2 else [(0, chunk), (size // 2, chunk)]
            if full:
                spans = [(0, size)]
            for off, ln in spans:
                fh.seek(off)
                buf = fh.read(ln)
                if not buf:
                    return "unreadable"
                if any(buf):
                    return "has-data"
            return "zero" if full else "suspect"
    except OSError:
        return "unreadable"


def walk(roots, min_bytes, limit, full):
    stats = {"zero": [], "suspect": [], "has-data": 0, "unreadable": [], "visited": 0}
    for root in roots:
        if not os.path.exists(root):
            print("根目录读不了或不存在:", root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                p = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(p)
                except OSError:
                    continue
                if size < min_bytes:
                    continue
                stats["visited"] += 1
                verdict = probe(p, full=full)
                if verdict == "has-data":
                    stats["has-data"] += 1
                elif verdict == "unreadable":
                    stats["unreadable"].append(p)
                else:
                    alloc = real_allocated(p)
                    sparse = alloc is not None and alloc < size
                    stats[verdict].append((size, sparse, p))
                if limit and len(stats["zero"]) + len(stats["suspect"]) >= limit:
                    return stats
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--min-mb", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0, help="累计多少个疑似后停止")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    st = walk(args.roots, int(args.min_mb * 2 ** 20), args.limit, args.full)
    print("探查文件 %d 个（>= %.1f MiB），有内容 %d 个" % (st["visited"], args.min_mb, st["has-data"]))

    def dump(kind, title):
        rows = st[kind]
        gb = sum(r[0] for r in rows) / 2 ** 30 if rows else 0
        print("\n[%s] %d 个 / %.2f GiB —— %s" % (kind, len(rows), gb, title))
        for size, sparse, p in rows[:40]:
            print("   %8.1f MiB %s %s" % (size / 2 ** 20, "稀疏" if sparse else "    ", p))
        if len(rows) > 40:
            print("   ...另 %d 个" % (len(rows) - 40))

    dump("zero", "逐字节确认为全零：内容已不可恢复，只能从别处重取")
    dump("suspect", "头尾取样全零但未逐字节确认（未加 --full）")
    print("\n[读不了] %d 个（权限或占用，不能当成「不存在」）" % len(st["unreadable"]))
    for p in st["unreadable"][:10]:
        print("   ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
