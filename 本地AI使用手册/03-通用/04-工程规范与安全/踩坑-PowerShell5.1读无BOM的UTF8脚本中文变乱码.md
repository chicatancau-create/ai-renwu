---
title: "PowerShell 5.1 读无 BOM 的 UTF-8 脚本，中文变乱码并打断解析"
date: 2026-10-10
domain: common
category: 03-通用/04-工程规范与安全
status: verified
severity: medium
stack: [PowerShell, Windows, 编码]
tags: [编码, 脚本交付, Windows]
---

# 问题：AI 生成的 .ps1 含中文路径/字符串，`powershell -File` 报"缺少右括号"之类的语法错

## 一句话结论

Windows PowerShell 5.1 按 ANSI(GBK) 读**无 BOM** 的 UTF-8 `.ps1`，中文字节被拆坏，字符串边界错乱，
报出来的却是语法错。**写 .ps1 必须带 UTF-8 BOM（+ CRLF）**，或者脚本里干脆不出现中文。

## 触发条件与影响

- 项目或功能：用脚本驱动 Excel COM 导出 PDF（含中文目录名）。
- 环境与版本：Win11 + `powershell.exe`（5.1），文件由 Python/编辑器以 UTF-8 无 BOM 写出。
- 触发条件：`.ps1` 内有中文路径或中文字符串字面量。
- 影响范围：脚本一执行就 ParserError，报错位置指向"foreach 表达式后缺少 ')'"，看不出是编码问题。

## 复现步骤

1. 前置条件：写一个含中文路径的 `.ps1`（UTF-8 无 BOM，LF 换行）。
2. 操作或命令：`powershell -NoProfile -ExecutionPolicy Bypass -File xxx.ps1`
3. 预期结果：正常执行。
4. 实际结果：`ParserError: 表达式或语句中包含意外的标记`，且乱码回显。

## 证据

同一份脚本内容，仅把编码改成 `utf-8-sig` + CRLF 后立刻正常执行并输出 `ALLDONE`；
期间还踩到第二个坑：在 bash 里用 `python -c "..."` 内联生成脚本时，`\A`、`\2` 等被当转义序列
（`SyntaxWarning: invalid escape sequence`），把中文路径写坏 —— 生成脚本要落到 .py 文件里用 raw 字符串。

**2026-10-14 补充第三种形态：双 BOM。** 用 `Path(...).write_text('\ufeff' + body, encoding='utf-8-sig')`
想"确保有 BOM"，结果 `utf-8-sig` 自己又写了一个，文件开头是 `EF BB BF EF BB BF`。
PowerShell 5.1 只认前一个当 BOM，第二个被当成正文首字符，于是第一行变成 `?$ErrorActionPreference`：

```
?$ErrorActionPreference : 无法将“?$ErrorActionPreference”项识别为 cmdlet、函数、脚本文件或可运行程序的名称。
所在位置 G:\...\verify-tray-registered.ps1:1 字符: 1
```

注意它**不是语法错**，而是 CommandNotFoundException，且 `ErrorActionPreference='Stop'` 因这一行没生效而继续往下跑，
后面每个错误都单独冒出来 —— 比原记录的 ParserError 更难归因，因为看起来像"脚本逻辑全坏了"。

## 根因分析

- 已确认的根因：PowerShell 5.1 读脚本时，无 BOM 一律按当前 ANSI 代码页解码；UTF-8 的中文字节被当 GBK 双字节吃掉半个，破坏引号配对。
- 排除过的假设：不是执行策略问题（`-ExecutionPolicy Bypass` 已给）；不是路径真不存在（同路径在 Python 里可读写）。
- 问题归属：本次修改引入（交付脚本的编码选择）。

## 最小修复

```python
open('x.ps1', 'w', encoding='utf-8-sig', newline='\r\n').write(body)   # body 用 raw 字符串写
```

或在脚本里彻底避免中文：用 `Get-ChildItem -LiteralPath` + 通配、或把路径当参数从别处传。

## 验证记录

- [x] 手动回归：改编码后同一脚本连续跑通（Excel COM 打开/导出/关闭）。
- [x] 同坑复现于另一台场景：`.cmd/.bat` 侧同类问题（见关联记录的 GBK 条目）。
- [ ] 自动化测试：未做（一次性交付脚本）。

## 可复用规则

**在 Windows 上生成给 PowerShell 用的脚本，编码固定 `utf-8-sig` + CRLF；生成 .cmd/.bat 则反过来用 GBK。**
判据：报"语法错/缺少括号"而脚本肉眼没问题时，**先怀疑编码，再读逻辑**。
**加 BOM 只有一条通道**：交给 `encoding='utf-8-sig'`，正文里**绝不再手写 `\ufeff`**；
拿不准就 `xxd file.ps1 | head -1`，开头只允许出现一次 `efbbbf`。
更省事的办法仍是首选：**脚本正文保持纯 ASCII**，中文从参数或别处传进来。

## 适用范围与不适用范围

- 适用：Windows PowerShell 5.1（`powershell.exe`）+ 任何含非 ASCII 的脚本文件。
- 不适用：PowerShell 7（`pwsh`）默认按 UTF-8 读，无此坑；纯 ASCII 脚本无此坑。

## 剩余风险

未在本机验证 `pwsh` 7 的行为差异（本机以 5.1 为主）；若脚本被别的编辑器重新保存，BOM 可能被去掉。

## 关联

- 相关记录：[[踩坑-openpyxl写的xlsx在Excel里行高被裁字]]
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码、命令或文档：`G:\AIrenwu\01_任务归档\2026-10-09_违纪表格式改造\03_工具脚本\gen_ps1.py`
