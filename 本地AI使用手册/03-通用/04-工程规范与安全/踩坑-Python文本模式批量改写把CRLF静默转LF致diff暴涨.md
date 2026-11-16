---
title: "Python 文本模式批量改写把 CRLF 静默转成 LF，38 处改动变成 2377 行 diff"
date: 2026-11-15
domain: common
category: 04-工程规范与安全
status: verified
severity: medium
stack: [Python, Windows, git, CRLF]
tags: [批量改写, 行尾, 假diff, 编码]
---

# 问题：只想替换 38 处路径，`git diff --stat` 却报 2377 行全变

> 事发 2026-11-13，2026-11-15 回写。

## 一句话结论

在 Windows 上用 `open(f, encoding='utf-8').read()` + `open(f, 'w', newline='').write()` 做批量替换，
**读取时的 universal newlines 已把 CRLF 折成 `\n`**，`newline=''` 只是「不再二次转换」，
于是整份 CRLF 文件被静默写成 LF —— 内容只改了几处，diff 却是整文件重写。
批量改写必须**按字节读写**，或读时显式 `newline=''` 保留原行尾。

## 触发条件与影响

- 项目或功能：对一批 Markdown 做正则替换（脱敏本机绝对路径）
- 环境与版本：Windows 10.0.28000；Python 3.14；仓库内 md 行尾**混用**（部分 CRLF、部分 LF）
- 触发条件：脚本用文本模式读 + `newline=''` 写，且未逐文件判断原行尾
- 影响范围：28 个文件里 13 个被整体改行尾；真实改动 38 处被埋进 2377 行噪声，
  审查者无法分辨「哪些是语义改动」，也会污染后续 `git blame`

## 复现步骤

1. 前置条件：一个 CRLF 行尾的文本文件，已提交进 git
2. 操作或命令：
   ```python
   s = open(f, encoding='utf-8').read()      # ← CRLF 在这里已变成 \n
   s = s.replace(old, new)
   open(f, 'w', encoding='utf-8', newline='').write(s)
   ```
3. 预期结果：`git diff --numstat` 只显示被替换的那几行
4. 实际结果：`git diff --stat` 报 `28 files changed, 2377 insertions(+), 2377 deletions(-)`

## 证据

同一文件改前改后的字节统计（本轮实测）：

```
03-执行计划/进度看板.md
  HEAD  CRLF: 197  LF-only: 0    bytes 12276
  NOW   CRLF: 0    LF-only: 197  bytes 12050     ← 少了 197 个 \r
```

而另一个本来就是 LF 的文件（`README.md`）改前改后都是 `CRLF: 0 / LF: 58`，**没有变化**
—— 说明这不是「git 规范化」，是脚本按文件原样破坏了行尾。

还原后同一批改动：`28 files changed, 76 insertions(+), 76 deletions(-)`（= 38 处替换）。

## 根因分析

- 已确认的根因：Python 文本模式默认 `newline=None`，**读**的时候把 `\r\n`、`\r` 统一翻译成 `\n`；
  写时 `newline=''` 表示「不做任何转换」，于是写出去的就是已被折叠的 `\n`。
  `newline=''` 常被误当成「保留原行尾」，它只保证不再叠加转换，**不会恢复读时丢掉的信息**。
- 排除过的假设：
  - 不是 `.gitattributes` 规范化 —— 该仓库只对 `*.sh` 设 `eol=lf`，md 无规则；
    且同批 LF 文件未被改动，方向不符。
  - 不是编辑器/IDE 改的 —— 改动全部由该脚本产生，`git diff` 内容与替换规则一一对应。
- 问题归属：本次修改引入（脚本写法），不是被改仓库的问题。

## 最小修复

**首选：按字节读写，行尾天然不动。**

```python
raw = open(f, 'rb').read()
s = raw.decode('utf-8')            # 只解码，不碰行尾
s = s.replace(old, new)
open(f, 'wb').write(s.encode('utf-8'))
```

若必须用文本模式，读和写都要 `newline=''`：

```python
s = open(f, encoding='utf-8', newline='').read()   # 保留 \r\n 原样
open(f, 'w', encoding='utf-8', newline='').write(s)
```

**已经改坏时的还原判据**：逐文件拿 `git show HEAD:<path>` 的字节数行尾，
只对「原本 CRLF 主导、现在变成纯 LF」的文件回灌 CRLF，不要全库统一转换
（本仓库 md 行尾本来就是混的，一刀切会制造新的假 diff）：

```python
old = subprocess.check_output(['git', 'show', 'HEAD:' + f])
new = open(f, 'rb').read()
if old.count(b'\r\n') > 0 and old.count(b'\n') == old.count(b'\r\n') \
   and new.count(b'\r\n') == 0 and new.count(b'\n') > 0:
    open(f, 'wb').write(new.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
```

## 验证记录

- [x] 破坏复现：改后 `git diff --stat` = 2377/2377；字节比对证明文件丢了 197 个 `\r`
- [x] 修复跑通：按上述判据逐文件还原后 `git diff --stat` = 76/76，与 38 处替换吻合
- [x] 未误伤：本来就是 LF 的文件（`README.md` 等 15 个）判为 `kept`，未被转换
- [x] 内容校验：仓库自带 source-only 校验通过（Markdown 625 份、Wiki 562、本地链接 614，0 错误）
- [x] 全仓门禁：还原并重签哈希清单后 `verify_all --profile=ci --offline` **21/21**

## 可复用规则

1. **批量改写文本文件一律按字节读写**（`rb`/`wb` + 显式 decode/encode）。
   需要按行处理时才用文本模式，且读写都带 `newline=''`。
2. 改完**先看 `git diff --stat` 的量级对不对**：预期改 N 处却出现「整文件行数 × 文件数」，
   立刻怀疑行尾/BOM/编码，不要急着提交。
3. 行尾还原必须**逐文件参照 HEAD 的原行尾**，禁止全库统一成 LF 或 CRLF。
4. 同类静默破坏还有 BOM（见关联记录）：文本模式读写同样会抹掉 UTF-8 BOM。

## 适用范围与不适用范围

- 适用：Windows 上对已入库文本做批量正则/字符串替换；行尾混用的仓库
- 不适用：本来就统一 LF 且 `.gitattributes` 强制 `eol=lf` 的仓库（转换无害，但仍建议按字节写）

## 剩余风险

- 若原文件是**混合行尾**（同一文件里既有 CRLF 又有 LF），上述还原判据会判为 `kept` 而不处理，
  此时仍可能残留少量行尾变化；本轮未遇到该情形，未覆盖。
- 按字节读写不会处理 BOM 之外的编码差异；源文件非 UTF-8 时需另行判定。

## 关联

- 相关记录：[[踩坑-ls-tree名字输出八进制转义致中文路径比对全错]]（同类：取数/写回通道静默改写内容；
  那条讲**比对**要归一化行尾，本条讲**写入**不能破坏行尾）、
  [[踩坑-沙箱只放行工作区致写E盘被拒且write会抹掉源码BOM]]（同类：文本写入抹掉 BOM）
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码：`E:\OBsidian\全栈工程师学习资料库`（脱敏提交 `76f143f`）
