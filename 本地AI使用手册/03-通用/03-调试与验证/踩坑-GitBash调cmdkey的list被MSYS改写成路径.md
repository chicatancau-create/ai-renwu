---
title: "Git Bash 里 cmdkey /list 只打印使用帮助，是 MSYS 把 /list 改写成了路径"
date: 2026-11-15
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: low
stack: [Git Bash, MSYS2, Windows, cmdkey]
tags: [命令行, 路径改写, 凭据, 排查]
---

# 问题：Git Bash 里 `cmdkey /list` 不列凭据，反而打印使用帮助

## 一句话结论

Git Bash（MSYS2）会把形如 `/list` 的参数当作 Unix 绝对路径改写成 `C:/Program Files/Git/list`，cmdkey 只看到一个非法开关就回使用帮助；命令前加 `MSYS_NO_PATHCONV=1`（或把开关写成 `//list`）即可。

## 触发条件与影响

- 项目或功能：查 Windows 凭据管理器条目（如 `git:https://gitcode.com`）。
- 环境与版本：Win11 28000，Git Bash（`D:\Git\bin\bash.exe`）。
- 触发条件：在 Git Bash 里运行任何用 `/xxx` 开关的 Windows 原生 CLI（cmdkey、schtasks、sc、robocopy 等）。
- 影响范围：命令看起来“坏了”，实际是 shell 改写过；照报错去修程序会走偏。

## 复现步骤

1. 前置条件：Git Bash 会话。
2. 操作：`cmdkey /list`
3. 预期结果：列出凭据条目。
4. 实际结果：打印 `CMDKEY [{/add | /generic}:targetname ...]` 使用帮助（中文 GBK，终端里还可能是乱码），没有任何凭据行。

## 证据

- 第一次 `cmdkey /list | grep -a -i ...` → 输出整段用法文本，说明 cmdkey 认为命令行参数不对，而不是“没有凭据”。
- 同一会话改为 `MSYS_NO_PATHCONV=1 cmdkey /list | grep -a -i ...` → 正常列出 `git:https://gitcode.com`、`gh:github.com:*` 等条目。
- 配套判据（既有记录）：目标名必须是 `git:https://<host>`（带 `https://`），写成 `git:gitcode.com` 会假阴性。

## 根因分析

- 已确认的根因：MSYS 的参数路径转换。单个以 `/` 开头的词被当作绝对路径，转换后 Windows 程序收到的是路径而不是开关。
- 排除过的假设：不是 cmdkey 版本问题，不是权限问题——同一用户、同一终端只加环境变量就恢复。
- 问题归属：环境/工具链行为，非程序缺陷。

## 最小修复

```bash
MSYS_NO_PATHCONV=1 cmdkey /list
# 或
cmdkey //list
```

中文输出按 GBK 处理；grep 加 `-a` 防止被当二进制截断。

## 验证记录

- [x] 对照实验：不加 env 打印用法；加 env 输出凭据列表（本轮实跑）。
- [ ] 未逐一实测 schtasks/sc 等其他工具，但同属一条路径改写机制（推断，未验证）。

## 可复用规则

在 Git Bash 里调用 Windows 原生 exe 时，凡参数以单个 `/` 开头（开关/选项），先加 `MSYS_NO_PATHCONV=1` 再判断程序行为。判据：输出的是“程序自己的使用帮助”而不是“找不到参数”时，优先怀疑 shell 改写过。

## 适用范围与不适用范围

- 适用：Git Bash/MSYS2 调 Windows CLI 的开关参数。
- 不适用：cmd.exe、PowerShell 自身的参数解析；WSL。

## 剩余风险

未发现已知剩余风险。

## 关联

- 相关记录：[[踩坑-Gitee仓库401分不清缺凭据还是缺权限且fill探测会回显密钥]]、[[规则-GitCode令牌只读活验用api-v5用户端点]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
