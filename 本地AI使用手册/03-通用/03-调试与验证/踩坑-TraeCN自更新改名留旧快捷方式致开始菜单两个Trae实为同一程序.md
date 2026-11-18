---
title: "开始菜单「两个 Trae」实为同一程序：Trae CN 自更新改名（TraeCode CN→TRAE CN）新增快捷方式未删旧名"
date: 2026-11-18
domain: common
category: 调试与验证
status: verified
severity: low
stack: [Windows 11, Trae CN 3.4.20, Inno Setup, .lnk]
tags: [快捷方式, 改名, 自更新, 重复入口, 取证, Trae, 启动模式, Agent]
---

# 问题：开始菜单里 TraeCode CN 和 TRAE CN 两个条目，像装了两个 Trae

## 一句话结论

本机只装了一个 Trae CN。2026-11-18 ~15:08 的自更新（Inno Setup 覆盖升级到 3.4.20）把显示名从
**TraeCode CN** 改成 **TRAE CN**，升级新建了「TRAE CN.lnk」却没删初装时的「TraeCode CN.lnk」，
两个快捷方式 TargetPath 完全相同（`D:\Trae CN\Trae CN.exe`）；用户两张截图里的「两个 IDE」也只是
同一进程树的两个工作区窗口（Obsidian 库 / AIrenwu 任务区）。**非双安装、非国际+国内双版。**
清理已于 2026-11-18 分两步执行：先**删升级新增的重复 TRAE CN.lnk，保留旧名 TraeCode CN.lnk**（用户 m00108 指定它是唯一启动入口）；
再按用户 m00134 要求**把保留的旧 lnk 改名为 TRAE CN.lnk**（用户接受重新固定磁贴），并在用户设置写入
`"window.startupWindowType": "agent"`，**默认启动 Agent 模式而非 IDE 模式**（下次冷启动生效）；收尾时开始菜单文件夹也一并改名 `TRAE CN`。

## 触发条件与影响

- 触发条件：Trae CN 于 2026-09-18 初装（当时产品名 TraeCode CN）；2026-11-18 内置自更新覆盖升级到 3.4.20，产品名改回 TRAE CN。
- 影响：开始菜单 `TraeCode CN` 文件夹里出现新旧两个名字的入口，易误判为重复安装或双版本；无功能影响、无多余进程、无多余数据目录。
-  visibility：旧名 lnk 是开始菜单「编程工具」固定文件夹里唯一可见/固定的 Trae 磁贴；新名 lnk 只藏在所有应用的文件夹展开层，桌面/任务栏均无 Trae 固定项 → 用户视角「旧的是唯一能启动的快捷方式」。

## 复现步骤

1. 开始菜单 → 所有应用 → `TraeCode CN` 文件夹：同时看到 `TraeCode CN` 与 `TRAE CN` 两个条目。
2. 同一程序开两个工作区窗口时，任务栏/截图呈现「两个 IDE」，加深误判。

## 证据（2026-11-18 15:15–15:38 只读取证 + 清理复核）

- 卸载注册表唯一条目：DisplayName `TRAE CN (User)`，DisplayVersion `3.4.20`，InstallLocation `D:\Trae CN\`，UninstallString `"D:\Trae CN\unins000.exe"`，键 `{98EB0EF0-1DE3-4838-B14A-3B0DC4570E8B}_is1`。
- 进程：全部 IDE 进程 Path 均为 `D:\Trae CN\Trae CN.exe`（PID 2236/36824/49044/49192/49704，Electron 主+子进程）；无 Code/Cursor/Qoder/Obsidian/Windsurf 进程。
- 安装/数据目录单源：D:\ 根仅 `D:\Trae CN`；数据仅 `C:\Users\Admin\AppData\Roaming\Trae CN` 与 `C:\Users\Admin\.trae-cn`；`AppData\Local\Programs`、`Program Files`、`Program Files (x86)`、用户目录均无国际版 Trae。
- 开始菜单 `C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\TraeCode CN\` 内两个 lnk（清理前）：
  - `TraeCode CN.lnk` 创建 2026-09-18 17:19:28（初装旧名）；
  - `TRAE CN.lnk` 创建 2026-11-18 15:09:52（本次升级新增）；
  - WScript.Shell 解析两者 TargetPath 均 `D:\Trae CN\Trae CN.exe`，Arguments 空，WorkingDirectory `D:\Trae CN`，IconLocation `,0`（取目标 exe 默认图标，图标不旧）。
- 升级痕迹：`unins000.exe` LastWrite 2026-11-18 15:08:27、`unins000.dat` 15:09:52，大批文件 15:08–15:09 重写 → Inno Setup 覆盖升级。
- 版本身份：exe VersionInfo FileVersion `2.3.103559` / ProductVersion `3.4.20`，CompanyName Beijing Yinli Catapult Technology Co., Ltd.；`D:\Trae CN\manifest.json` name `Trae CN`、packageType `stable_cn`、region CN、oversea false → 国内版单装。
- 清理后复核：文件夹仅余 `TraeCode CN.lnk`，CreationTime/LastWriteTime 仍 2026-09-18 17:19:28（原样未动），TargetPath 仍 `D:\Trae CN\Trae CN.exe`。

## 根因分析

- 事实：两 lnk 目标完全一致；创建时间分别对应「初装」与「本次升级」；卸载注册表、进程 Path、数据目录均单源。
- 推断：安装器跨版本改了产品显示名，升级按新名建快捷方式，但旧名快捷方式由旧版安装器以不同名字写入，不在新版卸载/升级清单里，故残留。
- 两窗口为 VS Code 系多工作区窗口，同一进程树，不是两个程序。

## 最小修复（已执行 2026-11-18，三步）

- 非故障，无需修程序。清理决策经用户拍板反转（用户 m00108：「把这个快捷键修复，这是这台机器中唯一能启动它的快捷键」，圈的是旧名 TraeCode CN）：
  - **删**：升级新增的重复 `TRAE CN.lnk`（Remove-Item -LiteralPath 精确路径）。
  - **保留**：`TraeCode CN.lnk` 原样不动——它是开始菜单唯一固定/可见的启动磁贴，且本身属性全对。
- 第二步（用户 m00134：「你把它的名字改一下」）：`Rename-Item` 保留的 `TraeCode CN.lnk` → `TRAE CN.lnk`；创建时间戳 2026-09-18 17:19:28 保留，目标/参数/图标不变。代价：开始菜单固定磁贴按 lnk 路径绑定，改名后「编程工具」文件夹旧磁贴失效，**需用户重新固定**（用户知情接受）。
- 第三步（用户 m00134：「启动的时候默认不要启动 IDE 模式，启动 Agent 模式」）：`C:\Users\Admin\AppData\Roaming\Trae CN\User\settings.json` 追加 `"window.startupWindowType": "agent"`，其余配置一律未动。
  - 机制（代码取证 `D:\Trae CN\resources\app\out\main.js`，模块 out-build/vs/platform/window/common/runtimeWindowStartup.js）：配置键 `iQ="window.startupWindowType"`；`gb()` 经 `hAe` 门槛后读值（SOLO 版与 SPRING 企业账号受限，CN 个人版通过）；启动决策 `fAe(t,e,i)`：`i==="agent"→$e.Agent` 显式配置优先 > `runtimeWindow.lastTask` 持久化窗口类型 > 上次 `lastActiveWindow.windowType` > 默认 `$e.Agent`。窗口类型枚举 `$e`：IDE/Agent/Floating/TraeWork。
  - 排除路径：`bin\trae-cn.cmd --help` 无模式参数（chat/serve-web/tunnel 子命令无关）；CLI 解析器无 agent 开关 → **唯一官方覆盖入口是该设置**，别找快捷方式参数。
  - 下次冷启动（完全退出所有窗口再启动）生效；不影响正在运行的窗口。
- 第四步（收尾，用户 m00242「该清的清，该收的收」授权）：开始菜单文件夹 `TraeCode CN` 一并 `Rename-Item` → `TRAE CN`，最终入口 `C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\TRAE CN\TRAE CN.lnk`；赶在用户重新固定磁贴前改完，避免磁贴二次失效。卸载器若按旧路径删快捷方式可能留残影，属可接受残留。

## 验证记录

- [x] 复现：开始菜单目录 listing 见两个 lnk 条目。
- [x] 定位：两 lnk TargetPath 一致 + 创建时间吻合初装/升级 + 卸载注册表单条目 + 进程 Path 单源。
- [x] 排除：无第二安装目录、第二数据目录、国际版进程；桌面/公共桌面/任务栏固定无其他 Trae lnk。
- [x] 清理回归（2026-11-18）：删新 lnk 后文件夹仅余旧 lnk，旧 lnk 时间戳未变、目标有效 → 单一入口且启动能力保留。
- [x] 改名回归（2026-11-18）：文件夹仅余 `TRAE CN.lnk`，CreationTime/LastWriteTime 仍 2026-09-18 17:19:28，TargetPath 仍 `D:\Trae CN\Trae CN.exe`。
- [x] 配置落盘：settings.json 末行 `"window.startupWindowType": "agent"`，字面锚点 edit、未整文件重写，其余键未动。
- [x] 文件夹改名回归（2026-11-18 收尾）：Programs 下仅 `TRAE CN` 文件夹、内仅 `TRAE CN.lnk`，Target 不变；收尾快照见 `G:\AIrenwu\01_任务归档\2026-11-18_TraeCN入口清理与默认Agent模式\02_证据日志\收尾快照-20261118.txt`（进程段空 = Trae 当时未运行，正好可冷启动实测）。
- [ ] 端到端：完全退出 Trae 后经快捷方式启动应进 Agent 窗口（机制已代码取证；待用户一次实测勾选）。

## 可复用规则

- 判「电脑里两个 XX」看三张清单，不看图标/条目数量：① `Get-Process` 的 Path；② 卸载注册表（HKCU/HKLM Uninstall）；③ 开始菜单/任务栏 lnk 的 TargetPath（WScript.Shell 解析）。三清单同指一个 exe = 同一程序的多窗口/多入口。
- Inno Setup 系应用（有 `unins000.exe`）自更新改名会「新增新名快捷方式、不删旧名」；见新旧名并存先比 lnk 创建时间与目标，别急着卸载重装。
- 清重复入口只删 lnk；删前确认两目标一致。**保留哪个看「哪个是用户固定/可见的入口」，不机械保留与卸载注册表 DisplayName 一致的那个**；改 lnk 文件名会坏开始菜单固定磁贴，用户明确要改名时先告知需重新固定。
- Trae CN「默认启动 IDE 还是 Agent」由用户设置 `window.startupWindowType`（`agent`/`ide`，主进程 `fAe()` 显式优先）控制，不是 CLI 参数也不是快捷方式参数；应用存储里的 `workbench.soloMode.enabled` 只是模式状态，不是启动覆盖入口。

## 适用范围与不适用范围

- 适用：Windows + Inno Setup 自更新应用的重复入口/改名取证。
- 不适用：同目录真双版本混装（见关联「两安装器写同一目录」）；国内/国际真双安装（见关联 Qoder 规则，那种有两套独立数据目录）。

## 剩余风险

- 「编程工具」文件夹旧磁贴因改名失效，待用户按最终路径 `…\Programs\TRAE CN\TRAE CN.lnk` 重新固定；未固定前从所有应用文件夹启动（入口本身有效）。
- `window.startupWindowType` 端到端待一次冷启动实测；若未来版本改键名或 `hAe` 门槛，按机制节重新取证。
- 下次自更新若再改名可能再叠条目，按同判据处理。

## 关联

- [[踩坑-两安装器写同一目录致双版本混装-resources归后装者]]（真混装对照）
- [[踩坑-任务栏图标变白按AUMID查开始菜单快捷方式IconLocation]]（多 lnk = 多条目先例）
- [[规则-国内版与国际版Qoder两套记忆目录完全独立只能单向拷入并校验]]（真双安装对照）