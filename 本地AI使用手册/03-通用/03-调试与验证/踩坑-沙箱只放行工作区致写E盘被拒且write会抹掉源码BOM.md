---
title: "沙箱拒绝写工作区外路径，以及 write 工具会抹掉原有 UTF-8 BOM"
date: 2026-10-19
domain: common
category: 03-调试与验证
status: verified
severity: medium
stack: ["DSH", "PowerShell 5.1", "Node.js"]
tags: ["沙箱", "BOM", "编码", "写文件"]
---

# 踩坑：写工作区外路径被拒 + write 工具会吃掉源码 BOM

> 本条由 `SKILL.md` 症状索引引用（2026-10-19 发现正文缺失，本次补写）。
> **BOM 部分是 2026-10-19 本机实测**；**沙箱拒写部分已于 2026-11-12 在 workspace-write 会话补测证实**（见 B 节），升级为 `verified`。

## 一句话结论

- **已实测**：DSH 的 `write` 工具写回文件时**统一落 UTF-8 无 BOM**，原有 BOM 会被抹掉。
  对带 BOM 的 `.ps1`（PowerShell 5.1 必需）是**真实风险**：写完再执行会出现中文乱码 / 假语法错。
- **已实测（2026-11-12 补测）**：默认沙箱为 `workspace-write` 时，写会话工作区以外的路径会被拒。
  报错形态取决于写入程序：文件工具呈现 `[sandbox: file access denied under <mode> mode]` / `FS_SANDBOX_DENIED`；
  子进程（git/python）呈现各自的权限错误（如 `could not lock config file ... Permission denied`）。

## 触发条件与影响

- 项目或功能：任何"用文件工具改写已有脚本/配置"的场合
- 环境与版本：DSH Desktop；`pwsh` 实为 Windows PowerShell 5.1；OS `10.0.28000`（Win11）
- 触发条件：
  1. 改写一个**原本带 BOM** 的文本文件；
  2. 默认 `workspace-write` 沙箱下写工作区外路径。
- 影响范围：BOM 丢失会让 `.ps1` 中文变成乱码或"缺少右括号"之类的假语法错；
  沙箱拒绝只是写入失败，**不损坏文件**，但会中断任务。

## 复现与证据

### A. BOM 被抹掉（本会话实测，verified 依据）

```
1) 造一个带 BOM 的文件（前 3 字节 EF BB BF）：
   [System.IO.File]::WriteAllBytes(path, BOM + UTF8("hello-bom-probe"))
   -> 字节数 20，前三字节 239,187,191   （BOM 存在）

2) 用 write 工具改写同一文件（只加一行内容）

3) 复核：
   -> 字节数 48，前三字节 104,101,108  （= 'h','e','l'）
   -> BOM 存在 = False
```

结论明确：`write` 工具写回时**不保留**原 BOM。

### B. 沙箱拒绝（原为转述，2026-11-12 补测证实）

（2026-10-19 原文，历史记录）本会话文件策略为 `danger-full-access`，E 盘写入**成功**，当时**无法验证** `workspace-write`
下对 E 盘的拒绝行为，结论只来自 `SKILL.md` 描述与既有记录，属于**转述**。**2026-11-12 已在 `workspace-write` 会话补测证实，见下。**

**2026-11-12 补测（workspace-write 会话，已证实）**：

- `git config --global http.https://github.com.proxy ...` 写 `C:\Users\Admin\.gitconfig` 被拒：
  `error: could not lock config file C:/Users/Admin/.gitconfig: Permission denied`；
  同一命令在 `danger-full-access` 下重试成功（回读新值确认）。
- 同会话 memsearch CLI 写 `D:\uv\data\memsearch\milvus.db\LOCK` 亦被拒（PermissionError）。
- 结论：**拒写不限 E 盘，工作区外任意路径（C 盘用户配置、D 盘数据目录）都拒**；读不受影响。
  报错文案由写入程序自己给出，不一定是工具层的 sandbox 标记。

## 根因分析

- 已确认：`write` 工具按 UTF-8（无 BOM）序列化文本，BOM 被视为不可见前缀被丢弃。
- 已确认（2026-11-12）：沙箱拒写工作区外任意路径（C 盘用户配置、D 盘数据目录均命中）；错误形态取决于写入程序（见 B 节补测）。
- 问题归属：环境/工具行为，非项目代码缺陷。

## 最小修复 / 处置办法

1. **需要保留 BOM 时不要用 `write` 整文件覆写**：改用 PowerShell 带 BOM 写出
   （`Set-Content -Encoding UTF8BOM`，PS7）或
   `[System.IO.File]::WriteAllText($p, $text, (New-Object System.Text.UTF8Encoding($true)))`（PS5.1 可用）。
2. 写完**必须回读前 3 字节**核对：`0xEF,0xBB,0xBF`。
3. 目标在沙箱外时：优先写进工作区再复制，或请用户切换权限模式；`never` 审批策略下提权会被直接驳回。

## 验证记录

- [x] BOM：造 BOM → `write` 覆写 → 回读字节，确认 BOM 丢失（本会话实测）。
- [x] 沙箱拒绝：2026-11-12 在 `workspace-write` 会话补测——git 写 `C:\Users\Admin\.gitconfig` 被拒、memsearch 写 D 盘 LOCK 被拒；切 `danger-full-access` 后同命令成功。
- [ ] `edit` 工具是否同样抹掉 BOM：未测。
- [ ] 带 BOM 的 `.ps1` 被改写后执行失败：未做端到端复现。

## 可复用规则

1. 任何"改已有文件"的动作，先判断该文件是否依赖 BOM（`.ps1`、部分 `.cs`/`.bat`）。
2. 依赖 BOM 的文件，改完立刻回读前 3 字节；不要凭"读起来正常"下结论。
3. 把"读得到的编码"和"写进去的编码"分开验证 —— 前者正常不代表后者保留了 BOM。

## 适用范围与不适用范围

- 适用：本机 DSH 会话里改写脚本/配置类文件；任何需要 PowerShell 5.1 正确解析中文的 `.ps1`。
- 不适用：纯 Markdown/JSON 等不依赖 BOM 的文件（丢失 BOM 无影响）。

## 剩余风险

沙箱行为会随权限模式变化，历史结论可能过期；每次遇到写入失败应先看当前文件策略模式，再决定处置方式。

## 关联

- 相关记录：[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]、[[规则-本地手册接入DSH成为默认前置与写Markdown的编码坑]]
- 相关分类：03-通用/03-调试与验证（本条现归属；BOM/编码姊妹记录在 04-工程规范与安全）
- 相关文档：`C:\Users\Admin\.dsh\skills\local-ai-handbook\SKILL.md`（症状索引「调试与验证」表引用本条）
- 移动注记：2026-11-13 由 `99-收件箱` 移入 `03-通用/03-调试与验证`（结构改动经用户放行「能修的就修」）；SKILL.md 症状索引路径已同步。
