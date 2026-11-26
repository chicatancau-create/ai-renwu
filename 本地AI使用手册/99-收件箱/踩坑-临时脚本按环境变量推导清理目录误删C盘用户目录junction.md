---
title: "踩坑-临时脚本按环境变量推导清理目录误删用户目录 junction"
date: 2026-11-19
domain: common
category: 工程规范与安全
status: needs-review
severity: high
stack: [Windows, PowerShell, Node.js]
tags: [删目录, junction, 软链接, 环境变量, 自毁脚本]
---

# 问题：验证脚本按 env 推导 home 并 rm，误删 C 盘用户目录下的 junction

## 一句话结论

用 `process.env.X || os.homedir()` 推导“临时目录”再 `rm -rf`，一旦环境变量赋值失败就会退化成删真实家目录；本次因 PowerShell `$home` 只读导致赋值失败，删掉了 `C:\Users\Admin` 下 24 个 junction（真实数据在 D 盘，未受损）。

## 触发条件与影响

- 项目或功能：为 DSH 插件写的临时冒烟测试脚本（自建临时 home 并在收尾清理）。
- 环境与版本：Windows 11 / PowerShell（`$home` 为只读自动变量）/ Node v24（ELECTRON_RUN_AS_NODE 运行）。
- 触发条件：`$home = "$env:TEMP\x"` 赋值抛错（只读变量），后续 `DSH_PROFILE_DIR` 变成 `C:\Users\Admin\profiles\desktop`，脚本把 `path.dirname(dirname(...))` 算成 `C:\Users\Admin`，末尾 `await rm(home, {recursive:true, force:true})`。
- 影响范围：`C:\Users\Admin` 下所有 junction（.dsh/.qoder/.claude/.codex/.vscode/... 共 24 个）被 unlink；实体目录（AppData/Documents/Pictures/Desktop/.ssh 等）未受损，因为删链接不递归。

## 复现步骤

1. 前置条件：家目录下的工具配置目录以 junction 方式指向其它盘（本机惯例：`C:\Users\Admin\.xxx` → `D:\DevCache\.xxx`）。
2. 操作或命令：脚本里 `const home = env.DSH_PROFILE_DIR ? ... : process.env.HOME`，收尾 `await rm(home, { recursive: true, force: true })`，而 HOME/DPROFILE 因赋值失败指向真实家目录。
3. 预期结果：只删临时目录。
4. 实际结果：报 `EBUSY: unlink 'C:\Users\Admin\NTUSER.DAT'`，同时 24 个 junction 已被删除。

## 证据

- 报错：`[Error: EBUSY: resource busy or locked, unlink 'C:\Users\Admin\NTUSER.DAT']`
- `Get-Item C:\Users\Admin\.dsh` 事后 `exists=False`；`D:\DevCache\.dsh` 完整。
- 修复后重建 23 个 junction：`restored junctions: 23`，`problems:` 空。

## 根因分析

- 已确认的根因：清理路径由环境变量推导，且没有“这是我创建的目录”的强断言。
- 排除过的假设：不是文件系统 bug；不是杀软；junction 目标数据未受影响（删链接不递归）。
- 问题归属：本次修改引入。

## 最小修复

- 重建 junction：`cmd /c mklink /J "C:\Users\Admin\.xxx" "D:\DevCache\.xxx"`；`.local` 因 billion-context 已重建为实体目录，改为 robocopy 合并原有内容。
- 脚本层面：删除所有临时测试脚本。

## 验证记录

- [ ] 格式化或静态检查：不适用
- [ ] 类型检查或编译：不适用
- [ ] 单元、集成或端到端测试：重建后用 `Get-Item ... .Target` 逐个核对 24 个链接目标，全部指向 `D:\DevCache\*`
- [ ] 构建：不适用
- [x] 启动或手动回归：AppData/Documents/Pictures 条目数与 mtime 与事发前一致；C 盘剩余 120.8 GB

## 可复用规则

1. 任何 `rm -rf`/`Remove-Item -Recurse` 的目标，必须先断言路径包含本次任务的唯一标记（如 `dsh-smoke-<uuid>`），断言失败直接抛错退出。
2. 临时目录用 `fs.mkdtempSync(join(os.tmpdir(), 'marker-'))` 创建并保留返回值，绝不用“反向推导上级目录”的方式得到 home。
3. PowerShell 里不要给 `$home/$pid/$host` 等自动变量赋值（只读，赋值失败后变量仍是旧值）。
4. Windows 上删除 junction 只删链接；但一旦脚本对 junction 目标继续递归，就会删真实数据 —— 删目录前用 `Get-Item .LinkType` 检查。

## 适用范围与不适用范围

- 适用：任何写临时脚本、做“建临时环境→跑→清理”的验证流程。
- 不适用：仅读取、不删除的脚本。

## 剩余风险

- 是否有 `C:\Users\Admin\Downloads` 等更早的 junction 无法确认（注册表 Downloads 指向 `G:\NDM下载`，推测从未存在）；本会话非管理员，无法用 USN 日志做穷举核对。

## 关联

- 相关记录：无
- 相关分类：03-通用/04-工程规范与安全
- 相关代码、命令或文档：DSH 插件 `G:\AIrenwu\03_备份\archived-cleanup-20261115`（测试对象）
