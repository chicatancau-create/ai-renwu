---
title: "Windows 上让所有新窗口默认居中：没有系统设置，只能常驻监视器"
date: 2026-10-11
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: low
stack: [Windows API, Python ctypes, PowerToys, PowerShell]
tags: [桌面自动化, 取证, 窗口管理]
---

# 问题：想让"所有软件打开时都居中"，系统设置和 PowerToys 都做不到

## 一句话结论

Windows 没有全局"新窗口居中"开关；PowerToys 0.100.2 的 FancyZones 也只有"回到该应用上次所在区域"，
**没有全局项**。可行做法是一个常驻监视器：轮询顶层窗口，只移动新出现的、且只移动不改尺寸。
落地时有 6 个必踩的坑，见下。

## 触发条件与影响

- 环境与版本：Win11 28000 + 2560×1600 @125%（工作区 2560×1540）+ PowerToys 0.100.2 + Python（D:\PyCharm\Python）。
- 触发条件：需要桌面窗口位置自动化。
- 影响范围：常驻进程影响所有窗口，必须带白名单与一键回滚。

## 六个坑（都实测过）

1. **DPI 未感知 → 坐标全错**。不调 `SetProcessDpiAwarenessContext(-4)` 时拿到的是虚拟化坐标；
   感知后 `GetWindowRect` 给物理像素（2560 宽），不感知会看到 2048。
2. **`GetWindowRect` 含隐形边框**，用它算居中会偏。要用 `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS=9)`
   取**可见框**算边距，位移后再把 `GetWindowRect` 的真实坐标加同样的 delta 移动。
3. **DWM cloaked 的幽灵窗口**要跳过（`DWMWA_CLOAKED=14`）——headless 浏览器每个 target 一个隐身窗口，
   不过滤就会去移动根本看不见的窗。
4. **入场动画期不能插手**：同一窗口连续两轮矩形不变才动，否则和滑动动画打架。
5. **启动时不要"顺手把所有窗口都居中"**：首轮只登记已有窗口，之后只处理新出现的，否则一开机满屏乱跳。
6. **`pythonw.exe` 下 `sys.stdout is None`**，直接 `print()` 会抛异常让常驻进程静默退出；
   注册自启前必须判空。日志还要带大小轮转，否则无限涨。

另外两条老坑复现了：PowerShell 5.1 读**无 BOM 的 UTF-8** `.ps1` 会把中文路径吃成语法错
（脚本里干脆不写中文，用 `$PSScriptRoot` 拼路径）；控制台回显注册表里的中文是乱码，
**判存在性要用 Python `winreg` 读，不要信控制台**。

## 判"能不能用现成工具"的方法

先读工具的 settings 树再下结论，别凭印象：
`%LOCALAPPDATA%\Microsoft\PowerToys\FancyZones\settings.json` 递归打印所有 `properties.*.value`，
确认没有全局居中项（`fancyzones_appLastZone_moveWindows` 只是"回上次区域"，且默认 False）。

## 验证记录

- [x] 单窗口端到端：新开的记事本 `328,251 → 327,204`，四边距 327/327/204/204，偏差 +0,+0。
- [x] A/B 基准量化：可见桌面等距 vs 物理屏幕等距（后者上 234、离任务栏仅 174，视觉偏下），已交用户选择。
- [x] 只移动不改尺寸：1906×1132 的窗移动前后尺寸一致。
- [x] 已有窗口不被动：监视器启动前开着的记事本位置未变。
- [x] 自启注册核对：`winreg` 读回 `HKCU\...\Run\WindowCenter`，两个路径 `os.path.exists` 均为真。
- [ ] 真实重启后自启：未执行，不写成通过。
- [ ] 多显示器：本机只有一块屏，未测。

## 可复用规则

桌面自动化类需求，先按「① 系统设置有没有 → ② 已装工具的配置树里有没有对应开关 → ③ 才自己写常驻」的顺序查；
写常驻必须同时交付**一键回滚脚本**和**配置里的总开关**，并把"不动哪些窗口"写清楚。
量化边距一律用可见框 + 所在显示器工作区，别用主屏工作区硬编码。

## 适用范围与不适用范围

- 适用：单/多显示器的 Windows 桌面自动化、需要"新窗口位置"策略的场合。
- 不适用：需要精确控制窗口尺寸的场景（本方案刻意不改尺寸）；对自带窗口管理器的终端/IDE 内部布局无效。

## 剩余风险

自己管位置的软件（IDE 分屏、视频浮窗、远程桌面）可能与监视器互相拉扯，需按进程名加 `skip_processes`；
200ms 轮询的 CPU 占用未量化。

## 补充：2026-11-13 实测复核（目录改名 + 自启机制迁移）

- **项目目录已改名**：`G:\AIrenwu\2026-10-10_窗口默认居中` 已不存在，现名 `G:\AIrenwu\01_任务归档\2026-10-10_桌面核心脚本`（`03_工具脚本` 下 watch.py / session_end.py / measure.py / doctor.py / register.ps1 / unregister.ps1 六脚本齐全，另有 tmp 备份）。11-11/11-12 各记录已用新名。
- **自启从 Run 键迁到计划任务**：HKCU `Run\WindowCenter` 已不存在；计划任务 `\WindowCenter` 现状态 **Running**；`watch.py` 实际在跑（PID 36368，`pythonw.exe`，命令行指向新路径）。
- 「新窗口居中只能靠常驻监视器」的核心结论不变；注册方式与路径以现查为准。

## 关联

- 相关记录：[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]、[[踩坑-openpyxl写的xlsx在Excel里行高被裁字]]（同为"必须真实渲染/真实读数取证"）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：`G:\AIrenwu\01_任务归档\2026-10-10_桌面核心脚本\03_工具脚本\watch.py`、`measure.py`、`register.ps1`、`unregister.ps1`（目录 2026-11-13 实测已改名，原名 `2026-10-10_窗口默认居中`）
