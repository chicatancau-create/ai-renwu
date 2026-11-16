---
title: "PowerShell 控制台 CP936 与 OutputEncoding 不一致，导致读 UTF-8 文件回显乱码"
date: 2026-10-13
domain: common
category: 03-通用/04-工程规范与安全
status: verified
severity: medium
stack: [PowerShell 5.1, Windows, 编码, DSH]
tags: [编码, 控制台, 假乱码, 取证]
---

# 问题：`Get-Content` 读一个明明正确的 UTF-8 文件，回显全是 `妫€绱㈠苟`，差点误判成文件写坏了

## 一句话结论

在这台机器上，**控制台代码页是 936(GBK)，但 `[Console]::OutputEncoding` 报的是 utf-8(CP65001)**，
两者不一致。`Get-Content` 默认按**代码页**解码，于是把 UTF-8 文件的中文字节按 GBK 硬解，
**在内存里就已经是错的**，回显只是把已损坏的字符串显示出来。

**关键判据：乱码是「读」出来的，不是「显示」出来的。**
验证一个中文文件到底写对没有，**不要用 `Get-Content`，要用 `[IO.File]::ReadAllText($p,[Text.Encoding]::UTF8)`**
或用严格解码器；两者会给出完全相反的结论。

## 触发条件与影响

- 环境与版本：Win11 28000 + Windows PowerShell 5.1（`5.1.28000.3086`，Desktop）；
  `chcp` = **936**，`[Console]::InputEncoding` = **gb2312(936)**，`[Console]::OutputEncoding` = **utf-8(65001)**，
  `[Text.Encoding]::Default` = **gb2312(936)**。
- 触发条件：文件以 **UTF-8 无 BOM** 保存，且用 `Get-Content <path>`（不带 `-Encoding`）读取。
- 影响范围：**误判文件损坏**，进而去"修"一个本来正确的文件；也会误判校验脚本的结论。
  本次实际后果：验证自建的 skill 文件时看到满屏乱码，第一反应是「`write` 工具把中文写坏了」。

## 复现步骤

1. 前置条件：任取一个含中文的 UTF-8 无 BOM 文件（本例为 `~/.dsh/skills/local-ai-handbook/SKILL.md`）。
2. 操作或命令（两条对照，同一文件同一行）：
   ```powershell
   (Get-Content $p)[2]
   ([IO.File]::ReadAllText($p,[Text.Encoding]::UTF8) -split "`n")[2]
   ```
3. 预期结果：两条输出一致。
4. 实际结果：第 1 条输出 `description: 妫€绱㈠苟璇诲啓...`；第 2 条输出正常中文
   `description: 检索并读写本机《AI本地使用手册》...`。

## 证据

- **字节级根因证明**：`检` 的 UTF-8 字节是 `E6 A3 80`，用 GBK(936) 解这三个字节恰好得到 `妫€`；
  `索` 的 `E7 B4 A2` 解出 `绱`。与观察到的乱码逐字吻合。
- **内存态证明（排除"只是显示问题"）**：
  ```powershell
  $v = (Get-Content $p)[2]
  $v.Contains('检索并读写本机')   # False
  $v.Contains('妫')               # True
  ```
  字符串**在变量里就已是坏的**，不是输出阶段才坏。
- **长度证明**：同一行正确长度 **227** 字符，`Get-Content` 读出 **321** 字符（比值 1.41）。
  GBK 双字节解码把「3 字节 UTF-8 字」拆成「1.5 个 GBK 字」，长度必然膨胀——这是双击解码的典型指纹。
- **文件本身是好的**：用严格解码器（`UTF8Encoding($false,$true)`，遇到非法序列即抛）读全文件
  **PASS，无异常**；`[IO.File]::ReadAllBytes` 首三字节为 `2D 2D 2D`（`---`），**无 BOM**，符合预期。
- **显式指定编码即恢复**：`(Get-Content $p -Encoding UTF8)[2].Contains('检索并读写本机')` → **True**。
- 控制台状态实测：`chcp` → `Active code page: 936`；
  `[Console]::OutputEncoding` → `utf-8 / CP65001`（**与 chcp 不一致，这就是坑源**）。

## 根因分析

- **已确认的根因**：`Get-Content` 的默认解码依据是**当前代码页（ACP=936）**，而文件是 UTF-8 无 BOM，
  于是"UTF-8 字节 → GBK 解码"发生一次错误转码；控制台输出编码恰为 UTF-8，
  于是这个**已经损坏的字符串**被原样正确输出。显示环节没有错，**读取环节就错了**。
- **排除过的假设**：
  - 不是 `write` 工具写坏了文件（严格 UTF-8 解码 PASS，字节正确）；
  - 不是终端显示问题（变量内存态已损坏，且显式 `-Encoding UTF8` 后同一终端显示正常）；
  - 不是 BOM 问题（该文件本就无 BOM，加 BOM 只是让 `Get-Content` 自动识别，属绕过而非修根因）。
- **问题归属**：环境/工具用法（控制台代码页与 .NET 编码属性不一致），非本次修改引入。

## 最小修复

**读中文文件的取证动作固定用显式编码**，不要依赖默认：

```powershell
# ① 首选：完全绕开控制台代码页
[IO.File]::ReadAllText($path, [Text.Encoding]::UTF8)

# ② 用 Get-Content 时必须显式指定
Get-Content -LiteralPath $path -Encoding UTF8

# ③ 需要确认"文件字节本身是否合法 UTF-8"时，用严格解码器（非法即抛）
$strict = New-Object Text.UTF8Encoding($false, $true)
$null = $strict.GetString([IO.File]::ReadAllBytes($path))   # 不抛 = 合法

# ④ 需要看清控制台真实状态时，别只看 [Console]::OutputEncoding
chcp                                                          # 权威：实际代码页
[Text.Encoding]::Default.CodePage                             # ACP
```

**判据（最重要）**：乱码出现时，先问一句「**是读错了还是显示错了**」——
把内容取进变量后用 `.Contains('正确中文')` 判断，能立刻分开这两种情况。

## 验证记录

- [x] 复现：`Get-Content` 与 `ReadAllText(UTF8)` 对同一行给出乱码/正常两种结果，已存档原文。
- [x] 根因：字节级对应关系 `E6 A3 80`→`妫€`、`E7 B4 A2`→`绱` 逐字核对一致。
- [x] 内存态：`$v.Contains('检索并读写本机')` = False，证明非显示层问题。
- [x] 长度指纹：227 → 321 字符，与 GBK 双字节解码预期吻合。
- [x] 修复验证：`-Encoding UTF8` 与 `ReadAllText(UTF8)` 两种读法均得到正确中文。
- [x] 文件完好性：严格 UTF-8 解码全文件 PASS，无 BOM。
- [ ] 与 DSH 自带 `read` 工具的对照：未做（`read` 工具走宿主文件系统服务，不经控制台代码页，理论无此坑）。

## 可复用规则

**在中文 Windows 上处理含非 ASCII 的文本文件，读的一律显式指定 UTF-8；
用于判断"文件是否写坏"的结论，只能由 `[IO.File]::ReadAllText(...,UTF8)` 或严格解码器签字，
`Get-Content` 的默认输出不作为证据。**

这条与已有的两条记录构成同一族，但根因各不相同，别混：
- [[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]] —— 是 **`.ps1` 被解释器解码**时出错（报假语法错）；
- [[03-通用/03-调试与验证/踩坑-Bash内联传参吞PowerShell变量与反斜杠|踩坑-Bash内联传参吞PowerShell变量与反斜杠]] —— 是**命令串被前置 shell 改写**；
- 本条 —— 是 **`Get-Content` 默认按代码页解码**，**出错在读取，不在执行也不在传参**。

## 适用范围与不适用范围

- **适用**：中文 Windows + Windows PowerShell 5.1 / 5.0，用 `Get-Content` 读 UTF-8 无 BOM 的含中文文件。
- **不适用**：PowerShell 7（默认 UTF-8，无此坑）；文件带 BOM（`Get-Content` 会自动识别）；
  纯 ASCII 文件；DSH 的 `read` 工具（走宿主 fs 服务，不经控制台代码页）。

## 剩余风险

未验证 `chcp 65001` 后 `Get-Content` 是否即恢复正常（改控制台代码页可能影响其它工具与子进程，
本机未实测，故未推荐把它当修复手段）。也未测 `.cmd` 侧是否有同族问题。

## 关联

- 相关记录：[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]（同属 PS 5.1 编码族，根因不同）、
  [[03-通用/03-调试与验证/踩坑-Bash内联传参吞PowerShell变量与反斜杠|踩坑-Bash内联传参吞PowerShell变量与反斜杠]]（同属"报错误导、先怀疑链路再动被测对象"）
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码、命令或文档：`chcp`、`[Console]::OutputEncoding`、`[IO.File]::ReadAllText($p,[Text.Encoding]::UTF8)`；
  本条发现于为 `~/.dsh/skills/local-ai-handbook/SKILL.md` 做接入验证时
