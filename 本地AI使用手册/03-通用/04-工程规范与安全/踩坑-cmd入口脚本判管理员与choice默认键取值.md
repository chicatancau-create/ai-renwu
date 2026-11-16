---
title: "写 .cmd 入口脚本：判管理员、UEFI 判定与 choice 默认键的取值"
date: 2026-10-12
domain: common
category: 03-通用/04-工程规范与安全
status: verified
severity: medium
stack: [Windows, cmd, batch]
tags: [脚本交付, Windows, 提权, 编码, 不可逆操作]
---

# 问题：桌面双击用的「重启进 BIOS」.cmd，提权判定和确认分支容易写错，写错就是真重启

## 一句话结论

自我提权的批处理**不能用 `net session` 判管理员**（它依赖 LanmanServer 服务，服务停了会把管理员误判成非管理员，
配合"非管理员就提权重开"就是死循环）；`choice` 的 `/D` 默认键要按 **`if errorlevel N` 是"大于等于 N"** 来排分支，
取消项必须放在数值最大的那一档并最先判。**不可逆命令（shutdown）只允许出现在确认之后。**

## 触发条件与影响

- 项目或功能：交付到桌面的 `重启进BIOS.cmd`（UEFI 固件设置重启）。
- 环境与版本：Win11 28000 + `cmd.exe`；`powershell.exe` 5.1 执行策略为 **Restricted**（双击 .ps1 会被挡，所以交付物只能是 .cmd）。
- 触发条件：脚本先判权限 → 再判固件类型 → 确认后执行 `shutdown /r /fw /t 12`。
- 影响范围：判据写错时要么无限弹 UAC，要么用户没确认就重启，正在跑的活儿全丢。

## 复现步骤

1. 前置条件：`.cmd` 以 GBK（无 BOM）+ CRLF 落盘，含中文提示。
2. 操作或命令（都在本轮实测过）：
   - 非管理员执行 `net session` 与 `fltmc`；
   - 非管理员执行 `bcdedit /enum {fwbootmgr}`；
   - `choice /C YN /T 5 /D N` 与 `choice /C 12N /T 5 /D N`，打印 `%errorlevel%`；
   - 提权后（`Start-Process -Verb RunAs`）再跑一次 `bcdedit /enum {fwbootmgr}` 并把结果写回 TEMP。
3. 预期结果：默认不按键 = 取消，不重启；非管理员时能诚实报告"判不了"。
4. 实际结果：见证据，全部符合预期。

## 证据

- `net session` 非管理员返回 **rc=2**（"发生系统错误 5。拒绝访问。"）；`fltmc` 非管理员返回 **rc=1**
  （"筛选器列表失败，出现错误: 0x80070005"）。两者当下都能当判据 —— 差别在服务依赖：
  `Get-Service LanmanServer` 本机现为 **Running**，所以 `net session` 今天"恰好可用"，属**潜在死循环**而非已发生故障。
- `bcdedit /enum {fwbootmgr}` 非管理员：**拒绝访问**；提权后成功输出「固件启动管理器 / 标识符 {fwbootmgr}」→ **本机是 UEFI**。
  所以固件类型判定必须在提权后做，体检模式在无权限时不能把结果写成"非 UEFI"（我第一版就这么写错了，已改成"现在判不了"）。
- `choice /C YN /T 5 /D N` → errorlevel **2**；`choice /C 12N /T 5 /D N` → errorlevel **3**。
  因此取消分支写成 `if errorlevel 3 goto :cancelled` 在前、`if errorlevel 2 ...` 在后才正确。
- 生成的 .cmd：2891 字节、97 行 CRLF、0 个裸 LF、无 BOM，GBK 能整文件回读；
  `--check` 与非法参数分支各跑一次，rc=0，**没有发生重启**；8 个标签与全部 `goto`/`call` 目标一一对应，无孤立标签、无缺目标。
- 提权通道实测：`Start-Process -Verb RunAs` 能起来并把只读结果写回 TEMP（本机可用）。

## 根因分析

- 已确认的根因：三个坑各自独立 —— ①权限判据依赖可被停用的服务；②需要在提权上下文里才能读到的信息被当成"判定失败"；
  ③`if errorlevel N` 的语义是"≥N"，与直觉的"等于"不同。
- 排除过的假设：不是 `choice` 不可用（本机在；只是不能当交互输入用重定向）；不是 ExecutionPolicy 影响 .cmd（只影响 .ps1）。
- 问题归属：本次修改引入（交付脚本自身的写法）。

## 最小修复

```bat
rem ① 判管理员用 fltmc，并用一次性环境变量兜住提权循环
fltmc >nul 2>&1
if errorlevel 1 (
  if "%BIOS_CMD_FROM_ELEVATION%"=="1" goto :noadmin
  set "BIOS_CMD_FROM_ELEVATION=1"
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

rem ③ 取消档最大、最先判
choice /C YN /T 30 /D N /M "确认现在重启？"
if errorlevel 2 goto :cancelled
shutdown /r /fw /t 12
```

配套的 .cmd 本机约束（同日实测/复用）：中文正文一律 **GBK 无 BOM + CRLF**；空行用 `echo(` 不用 `echo.`
（工作目录存在名为 `nul` 的文件时 `echo.` 会咬人）；不用 `timeout /t`（非交互执行报"输入重定向"错误），延时用 `ping -n`；
带非法参数时**必须打印用法**，不能静默退出。

## 验证记录

- [x] 静态检查：标签/跳转完整性用 Python 正则核对（缺目标 0、孤立标签 0）。
- [x] 编码检查：二进制读出 97 CRLF / 0 裸 LF / 无 BOM / GBK 全文回读通过。
- [x] 分支回归：`--check`（rc=0，无重启）、非法参数（打印用法 + pause）两条分支实跑。
- [x] 判据实测：`net session`=2、`fltmc`=1、`choice /D` 默认档=2/3、提权后 `{fwbootmgr}` 存在。
- [ ] 端到端：正常流程（双击→UAC→真重启→固件界面）**未跑**，因为会真的重启本机。

## 可复用规则

**凡是"自我提权 + 执行不可逆命令"的入口脚本：权限判据选不依赖可停服务的那一个（fltmc），
再加一个"已提权重开过一次"的环境变量护栏；不可逆命令前面必须有带默认取消档的 `choice`，且默认档必须落在取消；
读不到就写"判不了"，不许把"无权限"写成"否定结论"。** 所有这类脚本先跑只读的体检模式再交付。
例外：本机 LanmanServer 正常时 `net session` 也能判对，换 fltmc 是预防，不是修故障。

## 适用范围与不适用范围

- 适用：Windows 上交付给用户双击的 .cmd/.bat 入口脚本；需要 `shutdown /fw`、`bcdedit`、`netsh` 等管理员命令的脚本。
- 不适用：PowerShell 7 / 纯 ASCII 脚本；不需要提权的脚本；`pwsh` 下 `-Verb RunAs` 以外的提权方式。

## 剩余风险

`shutdown /r /fw /t 12` 在本机固件上能否真的落到 BIOS 设置界面，未证实（不重启机器就验证不了）；
`{fwbootmgr}` 存在只证明固件启动管理器可读，不等于该机型支持 `/fw` 直达。用户第一次真跑时需要人在场。

## 补充：2026-11-13 实测复核（执行策略与产物位置）

- **执行策略已非 Restricted**：`Get-ExecutionPolicy -List` 实测 `CurrentUser=RemoteSigned`、`LocalMachine=Undefined`、MachinePolicy/UserPolicy=Undefined。本地新建的未签名 .ps1 现可直接跑；远程下载带 Zone 标记的仍被挡。工具会话内仍建议显式 `powershell -NoProfile -ExecutionPolicy Bypass -File`（宿主进程可能带更严的 Process 级策略）。
- **产物已搬家**：`重启进BIOS.cmd` 已不在桌面（桌面可见文件 0、lnk 计数 0，与 DeskBox 收纳记录一致），现位于 `E:\DeskBox\系统优化\重启进BIOS.cmd`，仍为 **2891 字节**（与记录一致，内容未变）。
- fltmc 判管理员判据、`choice` 的 ≥N 语义、`/fw` 直达未证实状态均不受影响。

## 关联

- 相关记录：[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码、命令或文档：`G:\AIrenwu\01_任务归档\2026-10-12_重启进BIOS脚本\03_工具脚本\make_bios_cmd.py`、交付物 `C:\Users\Admin\Desktop\重启进BIOS.cmd`
