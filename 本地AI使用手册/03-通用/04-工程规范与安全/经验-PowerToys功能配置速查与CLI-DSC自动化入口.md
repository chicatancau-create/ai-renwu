---
title: "PowerToys 功能配置速查与 CLI/DSC 自动化入口"
date: 2026-11-24
domain: common
category: 03-通用/04-工程规范与安全
status: verified
severity: low
stack: [PowerToys 0.102.3101, Windows 11, PowerShell]
tags: [PowerToys, 配置速查, CLI, DSC, Junction, 提权]
---

# 经验：PowerToys 功能配置速查与 CLI/DSC 自动化入口

> `verified`：2026-11-24 实读本机注册表/进程/配置，并实测 Settings CLI `--help` 与 DSC `get`；38 模块全量功能清单见任务归档报告（见「关联」）。

## 一句话结论

托盘红圈软件 = Microsoft PowerToys（本机 v0.102.3101，38 个模块开关、15 开 23 关）；以后调功能有四条入口：设置 GUI / Settings CLI / DSC v3 / 直改 json，其中 CLI 与 DSC get 已实测可用；**Settings CLI 在 WinUI3Apps 子目录，安装根直接调必报 CommandNotFoundException**。

## 触发条件与影响

- 项目或功能：需要摸透、启停、改热键或脚本化调整 PowerToys 各模块时。
- 环境与版本：本机 `PowerToys (Preview)` DisplayVersion 0.102.3101.0；安装目录是 Junction 到 D 盘；主进程提权运行。
- 触发条件：在安装根调 `PowerToys.Settings.Cli.exe` 报 CommandNotFoundException；不知道配置真源位置而盲改 C 盘副本。
- 影响范围：自动化脚本与后续功能调整任务。

## 复现步骤

1. 前置条件：PowerToys 正在运行（提权）。
2. 操作或命令：`& 'C:\Users\Admin\AppData\Local\PowerToys\PowerToys.Settings.Cli.exe' --help`。
3. 预期结果：输出子命令帮助。
4. 实际结果：CommandNotFoundException（"无法将…项识别为 cmdlet…"）；改调 `C:\Users\Admin\AppData\Local\PowerToys\WinUI3Apps\PowerToys.Settings.Cli.exe --help` 正常输出 list / status <module> / enable <module> / disable <module>。

## 证据

- 卸载注册表 DisplayVersion=0.102.3101.0；主配置 `powertoys_version=v0.102.3101`。
- `C:\Users\Admin\AppData\Local\PowerToys` LinkType=Junction、Target=`D:\DevCache\AppData-Local\PowerToys`（DSH-Guard 迁移）；配置/数据目录 `C:\Users\Admin\AppData\Local\Microsoft\PowerToys` 仍在 C 盘。
- Settings CLI `--help` 实测子命令：list / status / enable / disable。
- `PowerToys.DSC.exe get --module Awake --resource settings` 返回与 `Awake\settings.json` 一致的 JSON；`DSCModules\` 下 29 个 `microsoft.powertoys.*.dsc.resource.json`；PS7 Modules 已装 `Microsoft.PowerToys.Configure`（winget configure 可用）。
- 主 `settings.json` 的 `enabled` 映射 38 键；模块配置结构 `{"properties":{键:{"value":…}},"name","version"}`；热键对象 `{win,ctrl,alt,shift,code,key}`，code 为 VK 码。
- 38 模块逐条功能/热键/当前值/配置路径：`G:\AIrenwu\01_任务归档\2026-11-24_PowerToys功能摸底\01_报告\PowerToys功能与配置摸底.md`。

## 根因分析

- 已确认的根因：Settings CLI 随 WinUI3 重写放在 `WinUI3Apps` 子目录而非安装根；安装形态是「安装目录 Junction 到 D + 数据目录留 C」两段真源。
- 排除过的假设：不是 PATH 问题、不是组件缺失（exe 存在，只是目录不同）。
- 问题归属：环境或依赖（安装布局），非本次修改引入。

## 最小修复

- 自动化一律用全路径 `WinUI3Apps\PowerToys.Settings.Cli.exe`（list/status/enable/disable）或安装根 `PowerToys.DSC.exe get|set|test|export --module <模块> --resource settings`；读配置读 `properties.*.value`。
- 本次只摸底未改任何配置，无需回滚。

## 验证记录

- [x] 启动或手动回归：CLI `--help` 实测输出 4 子命令；DSC get Awake 与 settings.json 逐键一致；进程/注册表/配置均实读。
- [ ] DSC set/test/export 真写：未跑（会改用户配置，超出本次只摸底的范围）。
- [ ] 运行中热改 json 是否被 runner 回写：未验证。
- [ ] 格式化/类型/单元测试/构建：不适用（无代码改动）。

## 可复用规则

- 调 PowerToys 前先读主 `settings.json` 的 `enabled` 判开关，再读模块目录 `properties.*.value`；启停走 Settings CLI 或 DSC，不手改 `enabled` 映射。
- 适用条件：本机 0.102.x 布局；版本升级后用 `--help` 与 `DSCModules\` 目录复核 CLI/DSC 资源名。
- 例外：关闭模块（CmdPal/ZoomIt/PowerToys Run 等）本机无 settings.json，热键取文档默认，启用后才生成。

## 适用范围与不适用范围

- 适用：本机 PowerToys 功能摸底、模块启停、热键/配置脚本化调整、winget configure 声明式管理。
- 不适用：其他机器的安装布局（非 Junction、非提权）；PowerToys 源码级修改。

## 剩余风险

- DSC set/test/export 与热改回写未实测；QuickAccent `activation_key=2`、GrabAndMove `modifierKey=0` 枚举语义未在本机验证（设置页可见中文标签）。
- 提权主进程非提权 taskkill 杀不掉（须 `-Verb RunAs`）；删 Junction 目录会跟随联接回收 D 盘真源（见关联记录）。

## 关联

- 相关记录：[[经验-AppData缓存迁D盘复用DSH-Guard核心按组包装]]、[[规则-本机管理员提权可静默完成不要推给用户]]、[[踩坑-删联接目录会跟随联接回收真源须靠回收站元数据取证]]、[[03-通用/03-调试与验证/规则-Windows新窗口默认居中只能常驻监视器]]
- 相关分类：03-通用/04-工程规范与安全
- 相关代码、命令或文档：`G:\AIrenwu\01_任务归档\2026-11-24_PowerToys功能摸底\01_报告\PowerToys功能与配置摸底.md`；https://learn.microsoft.com/zh-cn/windows/powertoys/
