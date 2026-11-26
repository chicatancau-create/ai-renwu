---
title: "CrossDesk 便携版开不了登录前无人值守：三层门禁与 CLI 输出只上控制台"
date: 2026-11-26
domain: common
category: 03-调试与验证
status: verified
severity: high
stack: [CrossDesk, v1.7.7-20261124, Windows, 服务, 无人值守]
tags: [CrossDesk, 远程桌面, unattended, 便携版, 服务, CLI, 控制台, 租约]
---

# 问题：CrossDesk `--unattended-enable` 永远 exit 1 且无任何输出

> `verified`：复现、源码定位、修复、验证均完成（2026-11-26，本机 Win11 2560x1600 笔记本）。

## 一句话结论

便携 zip 版**设计上**不能开登录前无人值守（编译期 `CROSSDESK_PORTABLE` 使 `kAutostartRequiresElevation=false`）；换安装版后仍失败是因为 ① CLI 输出经 `AttachConsole+freopen("CONOUT$")` 只上控制台屏幕、重定向必空（看不到真实报错），② `--unattended-enable` 的 kClient 租约门禁要求 GUI 进程**完全退出**（WM_CLOSE 只缩托盘）。按「安装版 → 首启联网取 ID → taskkill /F GUI → 提权 enable」顺序即成功。

## 触发条件与影响

- 项目或功能：CrossDesk 被控端「无人值守/登录前可连」（服务随 Windows 启动、锁屏/未登录同 ID 可连）。
- 环境与版本：crossdesk v1.7.7-20261124；便携 zip 与 Inno 安装版均复现；Windows 11 x64。
- 触发条件：对便携版跑 `CrossDesk.exe --unattended-enable`；或安装版在 GUI 仍运行时跑同命令。
- 影响范围：无人值守开不了 → 手机在外网无法在未登录/锁屏时连入；且因输出为空极易误判为「命令坏了/权限不够」。

## 复现步骤

1. 解压便携 zip 到任意目录，启动 GUI 联网取得 ID 后，提权跑 `CrossDesk.exe --unattended-enable`。
2. 预期：服务变 Automatic、生成 `C:\ProgramData\CrossDeskUnattended\`。
3. 实际：exit 1；stdout/stderr 重定向到文件为 0 字节；`%ProgramData%\CrossDeskUnattended` 不存在。安装版在 GUI 运行时同样 exit 1。

## 证据

- 源码（tag v1.7.7-20261124，本地副本备份 `G:\数据备份\CrossDesk-portable-20261126\src\`）：
  - `autostart_task.h:10-15`：`#if !defined(CROSSDESK_DEBUG) && (!defined(CROSSDESK_PORTABLE) || !CROSSDESK_PORTABLE)` → `kAutostartRequiresElevation=true`，否则 false；便携版=false → 报 "Unattended startup requires the installed Release build"。
  - `main.cpp` `EnsureConsoleForCli`：`AttachConsole` + `freopen("CONOUT$")` → CLI 的 cout/cerr 只写控制台屏幕缓冲，**任何重定向都拿不到**；失败原因字符串（如 "Enable boot startup from the running GUI settings, or close the GUI first"）因此看不见。
  - `autostart_control.cpp` `SetServiceAutostart` 门禁顺序：SupportsServiceAutostart → 管理员 → kServiceCli 租约 → service/session_helper 文件存在 → **GuiPresent 则要求走 GUI 设置，否则抢 kClient 租约（运行中 GUI 持有该租约）** → 服务注册查询 → `SharedHostIdentity::Prepare` → 装服务+启动+自启任务。
  - `shared_identity.cpp`（`apps/desktop/src/platform/windows/service/`）：`GetConfigPath()=%APPDATA%\CrossDesk`（Roaming）、`GetCachePath()=%LOCALAPPDATA%\CrossDesk\cache`；identity.json/devices.json 在 **Roaming\CrossDesk\trusted-devices\**，GUI 首启即建。查错目录会误判「identity 缺失」。
- 本机实测：便携版带 GUI/不带 GUI 均 exit 1；安装版 GUI 运行时 exit 1；`taskkill /F` GUI 后提权 enable 立即成功（服务 Automatic+Running、`ProgramData\CrossDeskUnattended\{shared-identity.json,status.json,logs}` 生成、登录自启计划任务出现）。
- 附加坑：控制台若处于「选择/标记」模式（窗口被点选过），`WriteConsole` 阻塞 → CLI 与调用链整体挂起（本次 enable 成功后挂起即此因）；taskkill 挂起 PID 解除。

## 根因分析

- 已确认根因：三层叠加——便携编译门禁（设计如此）、CLI 控制台附着导致报错不可见、kClient 租约要求 GUI 完全退出。
- 排除过的假设：① 「没联网取得 ID」——GUI 左下已显示已连接服务器且 ID 可见，排除；② 「identity 未落盘/ACL 竞态」——文件一直在 Roaming 目录，排除；③ 「服务没装」——service-install/start 均 exit 0 且 Running，排除。
- 问题归属：上游设计门禁 + 本机操作顺序，非修改引入。

## 最小修复

1. 用 **Release 安装版**（Inno；`/DIR="D:\CrossDesk"` 可自定义盘符；本例静默参数不生效改走向导点击）。
2. 首启 GUI 联网取得 ID/密码（截图或 UI 读值）。
3. 提权 `taskkill /F /IM CrossDesk.exe`（WM_CLOSE 只缩托盘，不算退出）。
4. 提权 `CrossDesk.exe --unattended-enable`（用 `Start-Process -Wait -PassThru` 拿 exit code；`& exe` 对 windows 子系统不等待）。
5. 复核 `Get-Service CrossDeskService` = Automatic+Running、`C:\ProgramData\CrossDeskUnattended\status.json`（device_id/password/mode=service/online）、登录自启计划任务；再重开 GUI 供登录后使用。

## 验证记录

- [x] 启动或手动回归：status.json `device_id=469026189 mode=service online=true`；服务 Automatic+Running；计划任务「CrossDesk Autostart S-1-5-21-…-1000」Ready；GUI 重开后左下「已连接服务器」。
- [x] 隔离对照：便携版带/不带 GUI 均失败、安装版带 GUI 失败、安装版杀 GUI 后成功，四组对照成立。
- [ ] 格式化/类型/单测/构建：不适用（第三方闭源 GUI+服务）。

## 可复用规则

- CrossDesk 要「锁屏/未登录可连」必须安装版；便携版只能做登录后被控（服务随 GUI 退出而停）。
- 该程序 CLI 报错**永远不要指望重定向**；要诊断就看 exit code + 服务/文件状态变化，或读 `%ProgramData%\CrossDeskUnattended\logs`、`%LOCALAPPDATA%\CrossDesk\logs`。
- 凡「enable 类」命令先确认 GUI 真退出（任务管理器无进程），托盘图标消失≠退出。
- 控制台程序莫名挂起先查控制台是否被点进「选择」模式（标题栏出现「选择」字样），Esc 或 taskkill 解除。
- 查 identity/配置先分清 Roaming(`%APPDATA%`) 与 Local(`%LOCALAPPDATA%`) 两个目录，别查错就下「缺失」结论。

## 适用范围与不适用范围

- 适用：CrossDesk v1.7.x Windows 被控端部署无人值守；同类「CLI 附着控制台」程序的输出失踪诊断。
- 不适用：CrossDesk 控制端（手机/PC 客户端）连接问题；IP 直连模式配置（另见其 USER_GUIDE）。

## 剩余风险

- 安装版 Inno 静默参数 `/VERYSILENT` 本机不生效（引擎仍弹向导），自动化部署需 UI 点击或另查打包开关；`/DIR` 生效。
- 共享身份文件仅管理员/SYSTEM 可读，普通权限读 status.json 会 Access denied，属设计而非故障。

## 关联

- 相关记录：[[03-通用/03-调试与验证/踩坑-SnugWin建屏安全中止实为克隆到达误报-CCD数据库记扩展拓扑化解|SnugWin 建屏安全中止误报]]（同日同机另一远控组件）。
- 相关代码、命令或文档：源码本地备份 `G:\数据备份\CrossDesk-portable-20261126\src\`；部署脚本与日志同目录 `setup9.ps1`、`setup10` 输出；上游仓库 github.com/kunkundi/crossdesk tag v1.7.7-20261124。