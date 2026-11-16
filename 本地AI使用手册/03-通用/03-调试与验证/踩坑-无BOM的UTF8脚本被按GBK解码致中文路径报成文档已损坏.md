---
title: "无 BOM 的 UTF-8 .ps1 被按 GBK 解码，中文路径报成「文档已损坏」"
date: 2026-11-15
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [PowerShell 5.1, Word COM, Git Bash, Python]
tags: [脚本编码, BOM, 中文路径, COM, 误导性报错]
---

# 问题：`powershell -File` 跑的脚本若为「UTF-8 无 BOM」，脚本里的中文路径会被解码成乱码，而 Word COM 把它报成「文档可能已损坏」

> 上一版这条记录挂在收件箱，怀疑对象是「H 盘 / 网络位置 / 受保护视图 / `【】` 文件名 / 3 参数形式」。**五个候选全部被 A/B 排除**，真因是脚本文件自己的编码。

## 一句话结论

PowerShell 5.1 用 `-File` 读 `.ps1` 时，**没有 BOM 就按 ANSI（本机 GBK）解码**，于是脚本字面量里的中文路径在到达 Word 之前就已经是乱码；Word 打不开这个不存在的路径，却回一句「此文档可能已损坏」，把人往「文件坏了 / 盘符权限」方向带。规则：**含任何非 ASCII 字符的 `.ps1` 必须用 `utf-8-sig` 落盘**，判据是先看文件头三字节。

## 触发条件与影响

- 项目或功能：用 Word COM 把 `.doc` 转 `.docx` 以便 python-docx 解析
- 环境与版本：Windows PowerShell 5.1（`WindowsPowerShell\v1.0`）、Microsoft Word C2R、Git Bash `cat >` heredoc
- 触发条件：`cat > conv.ps1 <<'EOF'` 写出 UTF-8 **无 BOM** 的脚本，脚本内含中文路径
- 影响范围：所有经 Bash 工具落盘再 `powershell -File` 执行的脚本；报错文案与真因无关，会把排查引偏

## 复现步骤（2026-11-15 实测矩阵）

先造一个真·中文名的 `.doc` 样本（用 Python 写，保证文件名是正确 Unicode）：`H:\wtest\【示例】真中文名.doc`，24576 字节，文件头 `d0cf11e0a1b11ae1`（合法 OLE2）。

同一份脚本正文，只改文件编码：

| 脚本编码 | 文件头字节 | 结果 |
| --- | --- | --- |
| UTF-8 无 BOM | `0d 0a 24 45 72 72…`（`\r\n$Err`） | `RESULT FAIL Word 无法读取此文档，文档可能已损坏。` |
| UTF-8 **with BOM** | `ef bb bf 0d 0a 24 45…` | `RESULT OK pages=1` |

排除其它候选的 7 格矩阵（全部用**带 BOM** 脚本，或路径自洽）：

| # | 盘符 | 文件名 | 调用形式 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | 本地 C: | ASCII | `Open(1arg)` | OK |
| 2 | **H:** | ASCII | `Open(1arg)` | OK |
| 3 | **H:** | **`【示例】`** | `Open(1arg)` | OK |
| 4 | 本地 C: | ASCII | `Open(3arg)` | OK |
| 5 | **H:** | ASCII | `Open(3arg)` | OK |
| 6 | **H:** | **`【示例】`** | `Open(3arg)` | OK |
| 7 | 本地 C: | **`【示例】`** | `Open(1arg)` | OK |

盘符、中文方括号、位置参数三个候选**全部无罪**。

**决定性旁证**：那次「全 OK」的 7 格矩阵脚本本身是无 BOM 的，它 `Copy-Item` 出来的文件名是 `銆愮ず渚嬨€憇ample.doc` —— 也就是 `【示例】sample.doc` 的 UTF-8 字节被 GBK 解码后的样子。源和目的被同样地改写，所以自洽地成功了；而原故障里**目标文件是别人用正确 Unicode 建的**，改写后的路径就找不到东西了。这一条正好解释了「为什么同样含中文路径，有时能跑通」。

## 证据

- `Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='H:'"` → `DriveType=3`（本地固定盘）、卷名 `bangong`、剩余 241.5GB —— **不是网络位置**
- `HKCU:\Software\Microsoft\Office\16.0\{Word,Excel,PowerPoint}\Security\ProtectedView` **三个都不存在**（用默认值），受保护视图这条候选没有配置依据
- 无 BOM 运行输出经 `iconv -f GBK -t UTF-8` 才读得通：`RESULT FAIL Word 无法读取此文档，文档可能已损坏。`
  （顺带：这类输出 `grep` 会判成 binary 而静默吞掉，要 `grep -a` 或先 `iconv`）

## 根因分析

- 已确认的根因：PowerShell 5.1 对无 BOM 的 `.ps1` 按当前 ANSI 代码页（GBK）解码，脚本内非 ASCII 字面量在解析阶段即被破坏；Word COM 只是忠实地报告「按这个（已损坏的）路径打不开」。
- 排除过的假设：网络盘/受保护视图（DriveType=3 且 PV 键不存在）、`【】` 字符（第 3/6/7 格通过）、`Documents.Open` 的位置参数形式（第 4/5/6 格通过）、文件本身损坏（同一文件带 BOM 脚本可正常打开并统计页数）。
- 问题归属：**本次修改引入**（脚本是我用 heredoc 写的），不是环境也不是 Word 的 bug。

## 最小修复

含非 ASCII 的 PowerShell 脚本一律 `utf-8-sig` 落盘。经 Bash 工具时不要用 `cat > x.ps1`（写出的是无 BOM UTF-8），改用 Python：

```python
open('x.ps1', 'w', encoding='utf-8-sig', newline='\r\n').write(body)
```

落盘后**先验文件头**再执行：`open('x.ps1','rb').read(3) == b'\xef\xbb\xbf'`。

## 验证记录

- [x] 复现：无 BOM → FAIL，带 BOM → OK，同一份正文、同一目标文件
- [x] 排除：7 格矩阵证明盘符/中文方括号/参数形式均无罪
- [x] 旁证：无 BOM 脚本把文件名本身改写为 GBK mojibake（`銆愮ず渚嬨€憇ample.doc`），机制自洽
- [x] 配置核对：H: 为本地固定盘，Office ProtectedView 键不存在

## 可复用规则

1. **报错文案与真因无关时，先怀疑传给它的字符串本身。**「文档已损坏」的第一反应应该是「路径字符串是不是已经烂了」，而不是「文件坏了」。
2. 任何经 shell heredoc 落盘、再由 Windows 原生程序执行的脚本，只要含非 ASCII，**先查 BOM 再跑**。同族坑：Node 的 `.mjs`、Python 源码用 UTF-8 没问题，但被 PowerShell/cmd 读的那一层不行。
3. 判断「是不是编码问题」的快捷动作：把输出 `iconv -f GBK -t UTF-8` 再读一遍；能读出通顺中文就说明管道里是 GBK。
4. 做 A/B 时**一次只动一个变量**。原故障我同时换了盘符和调用形式，才会得出「H 盘打不开」的错误结论并挂了两周围栏。
5. 遇到「同样含中文路径，有时能跑通」这种矛盾现象，去查两边是否被**同样地**改写（自洽失败）——本例正是如此。

## 适用范围与不适用范围

- 适用：Windows PowerShell 5.1 用 `-File` 执行任何含非 ASCII 字面量的脚本；COM 自动化传中文路径；`cmd /c` 里嵌中文
- 不适用：PowerShell 7+（默认按 UTF-8 读无 BOM 脚本，本条不适用，跨版本前先确认用的是哪个 shell）；纯 ASCII 脚本；直接由 Python/Node 解释的脚本

## 剩余风险

- 只验证了 Word COM。Excel / PowerPoint COM 同族未测（机制相同，但没证据就别当已验证）。
- PowerShell 7 上的行为未测；若哪天默认 shell 换成 pwsh，本条结论要重新核。
- 若系统 ANSI 代码页不是 936（GBK），mojibake 的具体形态会变，但「无 BOM 被按 ANSI 解码」这个机制不变。

## 关联

- 相关记录：`03-通用/03-调试与验证/踩坑-Bash内联传参吞PowerShell变量与反斜杠.md`（同族但机制不同：那条是 `-Command` 内联时 bash 先改写；这条是 `-File` 读脚本时 PowerShell 自己按 ANSI 解码）
- 相关记录：`03-通用/03-调试与验证/踩坑-docx排版判据只能用Word实转PDF逐页目视-python-docx.md`（本例正是那条里「ps1 须 utf-8-sig 写盘，无 BOM 会被 ANSI 解码打乱中文路径」的根因确认）
- 相关分类：`03-通用/02-AI协作与提示词`
- 相关代码、命令或文档：实验脚本原在 `C:\tmp\wtest\`（`matrix.ps1` / `nobom.ps1` / `bom.ps1`），已随会话清理删除；按本文「复现步骤」可重建
