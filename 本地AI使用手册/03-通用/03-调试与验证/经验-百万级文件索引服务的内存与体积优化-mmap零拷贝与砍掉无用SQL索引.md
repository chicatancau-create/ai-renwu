---
title: 经验-百万级文件索引服务的内存与体积优化-mmap零拷贝与砍掉无用SQL索引
status: verified
date: 2026-11-25
tags: [性能优化, Python, mmap, SQLite, 内存占用, 全盘索引]
---

# 百万级文件索引服务的内存与体积优化：mmap 零拷贝 + 砍掉无用 SQL 索引

## 一句话结论

390 万条目的全盘索引服务，把 `bytes(mmap)` 整份拷贝改成直接 `mmap.find`、把偏移表从 memoryview 换成 `array`，**进程内存从 1.9 GB 降到 210 MB（降 9 倍）**；再确认 FTS5 与 `name` 索引在该架构下根本没人查，**索引库从 1190 MB 降到 731 MB（省 459 MB）**，建库时间从 158 秒降到 84 秒。

## 触发条件

- 自建的文件搜索服务需要把上百万条路径常驻内存，用于毫秒级子串检索。
- 现象：进程工作集 1.9 GB，用户抱怨吃内存；索引库 1190 MB，其中一大半是"不知道有什么用"的 SQL 索引。

## 复现步骤

1. 用 `os.scandir` 扫全盘，产出 390 万条记录（名称、路径、大小、时间）。
2. 用 `build_cache.py` 把所有小写名称/路径拼成两个大字节串，加偏移表，写成 `cache.bin`（657 MB）。
3. 引擎装载时写 `self._raw = bytes(mm)`，然后 `self._raw.find(needle)`。
4. 观察进程：工作集约 1.9 GB。

## 证据（2026-11-25 本机实测）

| 项目 | 优化前 | 优化后 |
| --- | --- | --- |
| 服务进程工作集 | 1956 MB | 209~215 MB |
| 服务进程私有提交 | ~1900 MB | 65 MB |
| index.db | 1190.3 MB | 731.0 MB |
| 缓存装载耗时 | 0.29 s | 0.02~0.03 s |
| 全量重建耗时 | 158.1 s | 84.0 s |
| `报告` 查询 | 45~50 ms | 51 ms |
| `pdf` 查询 | 47 ms | 84 ms |
| `README.md`（8.8 万命中） | 256 ms | 257 ms |

单独验证各 SQL 索引的价值（复制库做对照）：

- `DROP name_fts + VACUUM`：1190.3 → 889.0 MB，**省 301.3 MB**，DROP+VACUUM 耗时 12.7 s。
- 再 `DROP idx_name + idx_vol + VACUUM`：→ 768.4 MB（合计省 421.9 MB）。
- 实际重建后（不建任何辅助索引）：**731.0 MB**。
- 关键路径不受影响：`WHERE rid IN (...)` 走主键，50 行 0.6 ms；`COUNT(*)` 全表扫 36 ms（只在重建时的卷统计里跑一次）。

## 根因

1. **`bytes(mm)` 是深拷贝。** `mmap` 本身零拷贝，但 `bytes(mm)` 把 657 MB 全读进进程私有堆，还额外触发 657 MB 的文件页缓存，工作集直接翻几倍。`mmap` 对象**自带 `.find()`**（C 实现，性能与 `bytes.find` 同级），根本不需要转成 bytes。
2. **`memoryview` 没有 `.find()`。** 这是第一版被迫改用 `bytes` 的直接原因；正解不是退化成 bytes，而是"在整块 mmap 上按绝对偏移检索，用 base/end 把窗口限制在目标区域"。
3. **偏移表用 memoryview 切片遍历慢且占内存。** 每取一个元素都走 Python 对象协议；改 `array.array('i')` / `array.array('I')` 后每项 4 字节（3.9M 项约 47 MB，列表要 340 MB），`bisect` 直接吃 C 数组。
4. **FTS5 与 `name` 索引是历史遗留。** 它们是第一版"SQL LIKE 查询"引擎的产物；换成缓存内存检索后，SQL 只剩 `WHERE rid IN (...)` 取整行一条路径，全文索引彻底没人查。

## 最小修复

```python
# 1) 装载：保留 mmap，不要 bytes(mm)
mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
self.rids = array.array('i'); self.rids.frombytes(mm[pos:pos + n * 4])
noff = array.array('I'); noff.frombytes(mm[pos:pos + (n + 1) * 4])

# 2) 定位：直接用 mmap.find + 绝对偏移窗口
def _scan(self, needle, target, limit):
    offs, base, end = (self.noff, self._name_base, self._name_end) if target == 'name' \
                 else (self.poff, self._path_base, self._path_end)
    out, find = [], self._mm.find
    p = find(needle, base, end)
    while p >= 0 and len(out) < limit:
        i = bisect.bisect_right(offs, p - base) - 1
        if out and out[-1] == i or i < 0 or i >= self.n:
            p = find(needle, p + 1, end); continue
        out.append(i); p = find(needle, p + 1, end)
    return out

# 3) 取文本：偏移是相对区域起点的，必须加回 base
def _text(self, i, target):
    if target == 'path':
        b = self._path_base
        return self._mm[b + self.poff[i]:b + self.poff[i + 1] - 1]
    b = self._name_base
    return self._mm[b + self.noff[i]:b + self.noff[i + 1] - 1]

# 4) 只取前 N 条时用 nsmallest，不要全排序
page = heapq.nsmallest(offset + max_results, hits, key=key)[offset:offset + max_results]

# 5) 建库时不建 FTS5、不建 name/vol 索引
```

## 验证记录

- 优化后 9 种查询语法全部回归通过：`pdf` 3053、`报告` 177、`kaiju` 16、`*.gguf` 6、`ext:md 手册` 50、`folder:node_modules` 2754、`!node_modules ext:md` 197409、`path:AIrenwu 手册` 18。
- 全量重建连跑 3 次，`exit 0`，rows 3,906,112，`built_at` 正确更新。
- 冷启动全链路（杀看门狗+杀服务 → 跑启动项 vbs → 10 秒后）复验通过：`ok hwnd=31132838 pid=19356`，`报告` 177 条。
- 客户端端到端（DeskBox Alt+D 实际输入）全部 `IPC-MATCH=True`，`everythingMs` 27~50 ms。

## 可复用规则

1. **`mmap` 自带 `.find()` / `.rfind()` / `.startswith()`，别为了"能 find"就 `bytes(mm)` 深拷贝。** 大文件只读场景下 `mmap` 是零成本的。
2. **`memoryview` 没有 `.find()`。** 需要在大块只读字节上做子串定位时，优先 `mmap`，其次是 `bytes`。
3. **零点几秒的"装箱"开销值得算一遍。** 3.9M 条 × Python int 列表（28 字节/项）≈ 340 MB；`array('i')` 是 4 字节/项 ≈ 15.6 MB。
4. **索引是否存在，要用"代码里真的有没有查它"来判定，不能凭直觉。** 用 `grep` 把 `SELECT` 全列出来比猜可靠。
5. **SQLite 的辅助索引要按真实查询路径取舍。** 只有 `WHERE rid IN (...)` 和 `COUNT(*)` 的库，`name` 索引和 FTS5 纯属负担；`VACUUM` 后空间才会真正归还。
6. **"窗口存在"不等于"服务可用"。** 看门狗要额外发 `WM_NULL` + `SendMessageTimeout(SMTO_ABORTIFHUNG)` 探活，卡死两次就 `TerminateProcess` 重启。

## 适用范围

Python 3.11+ / Windows；任何"百万级条目 + 只读 + 需要毫秒级子串检索"的本地索引服务。SQLite 侧的结论（FTS5 与 name 索引可去）适用于"SQL 只做按主键取行"的架构，若改用 SQL 做检索则不适用。

## 剩余风险

- `mmap` 依赖操作系统文件页缓存：内存紧张时页面被回收，冷查询会从磁盘重读（实测首个查询约 84 ms，热态 50 ms）。
- 服务进程工作集读数会随访问范围波动（209 MB ~ 731 MB），这是映射页的常驻量，不是私有内存；私有提交稳定在 65 MB。
- 索引无增量更新，靠每日 03:30 全量重建（84 秒）保证新鲜度。

## 关联

- [[经验-自建Everything兼容IPC服务顶替原版-四点补齐与伪装常驻]]
- 实现文件：`D:\AI-Tool-State\fullindex\engine.py`、`build_db.py`、`build_cache.py`、`watchdog.py`
