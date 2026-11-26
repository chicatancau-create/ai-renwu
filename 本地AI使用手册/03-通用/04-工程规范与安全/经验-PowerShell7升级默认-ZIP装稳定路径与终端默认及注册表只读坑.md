---
title: "PowerShell 7 升级并设默认：7.7.0 已无 MSI，用官方 ZIP 装稳定路径 + 终端默认 + 注册表只读坑"
date: 2026-11-26
domain: common
category: "04-工程规范与安全"
status: verified
severity: medium
stack: ["Windows 11 Build 28000", "PowerShell 5.1（系统组件）", "PowerShell 7.7.0", "Windows Terminal 1.25.3131.0", "注册表 HKLM Environment", "winget"]
tags: ["PowerShell", "pwsh", "升级", "默认终端", "PATH", "REG_EXPAND_SZ", "注册表只读", "MSIX", "ZIP", "Windows Terminal", "提权"]
---

# 问题：终端默认还是 Windows PowerShell 5.1，要升到最新 7.x 并设默认、旧版能删就删

## 一句话结论

2026-11-26 把默认 shell 从 5.1 升到 **PowerShell 7.7.0**：官方 **7.7.0 已取消 MSI 安装器**（只剩 `.msixbundle` 和 `.zip`），为要稳定 exe 路径 + 真实 PATH 项，改用**官方 win-x64 ZIP 解压到 `C:\Program Files\PowerShell\7`**，系统 PATH 前置该项（保 `REG_EXPAND_SZ`），Windows Terminal 默认 profile 切到它并隐藏 5.1。**5.1 是 Windows 系统组件，无法卸载**，只能不设默认/隐藏。全部实测回读通过。

## 触发条件与影响

- 项目或功能：本机所有命令行/自动化（DSH、headroom、大量脚本）依赖的默认 shell
- 环境与版本：Windows 11 专业版 Build 28000；原默认 PS 5.1.28000；Windows Terminal 1.25.3131.0
- 触发条件：用户看到终端/选择器显示「管理员: Windows PowerShell 5.1」，要求升最新并设默认
- 影响范围：默认 shell 版本、`pwsh` 解析路径、终端默认 profile

## 关键事实（先查再动手）

1. **5.1 卸不掉**：`C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe` 是 Windows 组件，没有卸载入口。能做的只有「不设为默认 + 在终端里隐藏」，不要尝试删它。
2. **7.7.0 没有 MSI**：`winget show Microsoft.PowerShell` 安装器类型是 `msix`；GitHub v7.7.0 资产只有 `.msixbundle` 与 `.zip`（win-x64/x86/arm64/fxdependent），**无 `.msi`**。用官方 `hashes.sha256`（注意是 **UTF-16** 编码）核对。
3. **MSIX vs ZIP 取舍**：winget 默认装 MSIX 到 `C:\Program Files\WindowsApps\Microsoft.PowerShell_7.7.0.0_x64__8wekyb3d8bbwe`，靠 `WindowsApps\pwsh.exe` 别名解析，路径带版本号、不够稳。本机自动化重，选 **ZIP → 经典稳定路径 `C:\Program Files\PowerShell\7`** + 真实系统 PATH 项 + 显式终端 profile。

## 最小修复（可复现步骤）

1. **下载并校验**：官方 `PowerShell-7.7.0-win-x64.zip` 下到 `H:\下载`（C 盘不放下载实体），`Get-FileHash` 对官方 `hashes.sha256`。本次 sha256=`7c74e03b20a75b59715847439d046a6214b1863ee79b187872980f139bb4a05f`，115330228 字节，match=True。
2. **提权解压**：写 ASCII-only worker `.ps1` 到 `%LOCALAPPDATA%\Temp`，`Expand-Archive` 到 `C:\Program Files\PowerShell\7`，验证 `pwsh.exe -NoProfile -Command '$PSVersionTable.PSVersion'`=7.7.0。父进程 `Start-Process powershell -Verb RunAs -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',<worker>`（本机 `ConsentPromptBehaviorAdmin=0`，无 UAC 弹窗），worker 逐行 `Add-Content` 自写日志，父进程轮询 `DONE_OK/DONE_FAIL`。
3. **改系统 PATH（保类型）**：见下方「根因①」，必须用**可写**方式打开注册表键，前置 `C:\Program Files\PowerShell\7`，保留 `REG_EXPAND_SZ`，写后广播 `WM_SETTINGCHANGE`。
4. **去重**：若之前 winget 装过 MSIX，`Get-AppxPackage Microsoft.PowerShell | Remove-AppxPackage`（per-user 非提权即可），避免两份 7.7.0。
5. **终端默认**：改 `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json`，`defaultProfile` 指向 pwsh7 profile，5.1 profile `hidden:true`。**先备份**（本次 `H:\下载\pwsh7-backup\settings.json.bak-20261126-102720`）。见「根因②」避免 GUID 冲突。

## 根因分析（两个真坑）

- **根因①：`Get-Item` 打开的注册表键是只读，`SetValue` 必失败。** 提权 worker 里 `Get-Item 'HKLM:\...\Environment'` 后 `.SetValue('Path',...)` 报 `使用"3"个参数调用"SetValue"时发生异常:无法写入到注册表项。`——不是没提权（解压到 Program Files 已成功证明已提权），而是键句柄只读。**正解**：`[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Session Manager\Environment', $true)` 拿可写句柄再 `SetValue`。改 PATH 前先 `GetValueKind('Path')` 读类型、用 `GetValue(...,[RegistryValueOptions]::DoNotExpandEnvironmentNames)` 读原始值，写回时**沿用原 `REG_EXPAND_SZ`**，否则 `%SystemRoot%` 等会被展开写死。
- **根因②：Windows Terminal 会自动生成 PowershellCore 动态 profile，GUID 是知名常量，手动再加必撞。** 只要 PATH 里有 pwsh，WT 就自动生成 `source:"Windows.Terminal.PowershellCore"` 的 profile，GUID 固定 `{574e775e-4f2a-5b96-ac1e-a2962a402336}`。若再手动加一条同 GUID 的 profile → 重复 GUID 冲突。**正解**：不手动新增，直接在 WT 自动那条上定制 `name/icon/commandline`（commandline 指到 ZIP 的 `C:\Program Files\PowerShell\7\pwsh.exe`），**保留 `source` 字段**，WT 就不会再加重复。ZIP 不带 `.ico/.png`，icon 直接指 `pwsh.exe` 本体。5.1 profile `{61c54bbd-c2c6-5271-96e7-009a87ff44bf}` 设 `hidden:true`（可逆，非删除）。

## 验证记录

- [x] 解压后 `pwsh.exe` 直跑 `$PSVersionTable.PSVersion`=7.7.0、PSEdition=Core
- [x] 系统 PATH 回读：`C:\Program Files\PowerShell\7` 在最前，`path_kind_after=ExpandString`（类型保住），`contains_add=True`
- [x] **模拟新进程**：按注册表实时 machine+user PATH 展开合并，首个 `pwsh.exe`=`C:\Program Files\PowerShell\7\pwsh.exe`，version=7.7.0（当前工具进程 env 是旧的，必须按注册表实时值验，不能信 `$env:Path`）
- [x] 终端 settings `ConvertFrom-Json` 合法、无重复 GUID；`defaultProfile={574e775e...}`；唯一 pwsh7 profile commandline 指 ZIP exe；5.1 hidden
- [x] 去重：`zip=True`、`msix_alias=False`（仅一份 pwsh）；5.1 仍在（系统组件，预期）

## 可复用规则

1. **升 PowerShell 先查安装器形态**：7.7.0 起无 MSI；要稳定路径/自动化就用官方 ZIP 解到 `C:\Program Files\PowerShell\7`，别依赖 MSIX 的版本号路径 + 别名。
2. **写注册表一律用可写句柄**：`[Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($sub,$true)`；`Get-Item` 的键只读，`SetValue` 会报「无法写入到注册表项」。提权与否和键句柄读写是两回事。
3. **改 PATH 保 `REG_EXPAND_SZ`**：先 `GetValueKind` + `DoNotExpandEnvironmentNames` 读原始值，写回沿用原类型；改完广播 `WM_SETTINGCHANGE`，但**已跑进程仍读旧值**，验证要按注册表实时值模拟新进程。
4. **终端默认别手动撞 GUID**：WT 的 PowershellCore 动态 profile GUID 固定 `{574e775e-4f2a-5b96-ac1e-a2962a402336}`，在自动那条上定制并保留 `source`，不要另加同 GUID。
5. **5.1 是系统组件卸不掉**：只能不设默认 + 终端隐藏，别尝试删除。
6. **静默提权通路**：`ConsentPromptBehaviorAdmin=0` 时 `Start-Process -Verb RunAs -WindowStyle Hidden` 无弹窗；worker ASCII-only、自写日志到 `%LOCALAPPDATA%\Temp`、父进程轮询 `DONE_OK/DONE_FAIL`；`-Verb RunAs` 不能与 `-RedirectStandardOutput` 同用。
7. **备份先行 + 下载落 H 盘**：改终端配置先备份；安装包/下载实体放 `H:\下载`，C 盘只留临时产物且完工自清。

## 适用范围与不适用范围

- 适用：Windows 10/11 单机、要把默认 shell 升到 PowerShell 7 并设终端默认、重自动化需要稳定 pwsh 路径
- 不适用：域 GPO 托管的环境变量/终端策略（会被策略覆盖）；多用户共享机器（本次只处理当前用户 + 机器级 PATH）

## 剩余风险

- ZIP 版不在「应用和功能」里登记卸载入口（便携安装特性）；要卸载直接删 `C:\Program Files\PowerShell\7` + 移除 PATH 项 + 还原终端配置
- 已跑的终端/IDE/DSH 仍读旧 PATH，需重启才见 `pwsh` 新解析；新开的终端默认已是 7.7.0
- DSH 的 `pwsh` 工具内部仍按自身解析跑 powershell.exe 5.1，属 DSH 内部 shell 选择，超出本次范围未动

## 关联

- 相关记录：[[经验-环境变量体检与整理-失效路径重复PATH与缺失SDK变量]]（PATH 体检/保类型/广播同源）
- 相关分类：`03-通用\04-工程规范与安全`、`03-通用\03-调试与验证`
- 相关实物：安装包 `H:\下载\PowerShell-7.7.0-win-x64.zip`；终端配置备份 `H:\下载\pwsh7-backup\settings.json.bak-20261126-102720`；安装目录 `C:\Program Files\PowerShell\7`
