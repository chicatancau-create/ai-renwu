---
title: "资源管理器多出两个同名同容量的盘：那是 subst 映射，不是第二块磁盘"
date: 2026-11-08
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: low
stack: [Windows 11, subst, QueryDosDevice, CMake/Qt]
tags: [盘符, subst, 幽灵盘, 卷序列号, 构建脚本清理]
---

# 问题：此电脑里出现两个同名同容量的盘（AI 的 G: 与 Q:）

## 一句话结论

Q: 不是磁盘，是 `subst` 把 `G:\CodeWeave\.local\prep\qt\6.8.3\msvc2022_64` 映射成的盘符；
映射目标在 G 盘上，所以卷名、容量、可用空间与 G 完全相同。**判据是 `vol` 的卷序列号相同**。

## 触发条件与影响

- 环境：Windows 11；CodeWeave 的 Qt 构建脚本 `工程文件\工具\构建当前Qt.cmd`。
- 触发：构建中途被打断（关窗口/被杀），脚本末尾的 `subst %D%: /d` 没执行。
- 影响：只影响观感与"以为多了一块盘"；不影响数据（删盘符不删文件）。

## 复现步骤

1. 执行 `subst Q: G:\CodeWeave\.local\prep\qt\6.8.3\msvc2022_64`。
2. 打开此电脑：出现第二个「AI」盘。
3. `vol Q:` 与 `vol G:`：卷序列号相同；`Get-Partition` 与 `MountedDevices` 里都没有 Q。

## 证据

- `vol G:` / `vol Q:` 序列号均为 A265-2993。
- `QueryDosDeviceW('Q:')` → `\??\G:\CodeWeave\.local\prep\qt\6.8.3\msvc2022_64`。
- `HKLM\SYSTEM\MountedDevices` 共 14 项，无 `\DosDevices\Q:`；`Get-Volume` 只有 6 个卷。

## 根因分析

构建脚本为了绕开带空格/中文的 Qt 路径，临时映射一个盘符；正常结束会删，**被中断就不删**。
不是病毒、不是分区丢失、不是盘符冲突。

## 最小修复

```
subst Q: /D
```
注意事项：路径末尾有反斜杠时**不要加引号**（会被解析成 `\G:\...` 而报「找不到路径」）；
摘之前先确认没有进程在用（本次 `cmake -E env PATH=Q://bin ...` 正在跑测试）。

## 验证记录

- [x] 摘除后 `subst` 列表为空、`Win32_LogicalDisk` 无 Q:、`G:\` 与 G: 卷正常
- [x] 中途误摘 30 秒后立即恢复，核对当轮测试全部 `Test Passed` 且取证截图正常产出
- [ ] 未做：给 `构建当前Qt.cmd` 加失败兜底清理（需要改用户脚本，待其同意）

## 可复用规则

1. 「多出同名同容量的盘」先比 `vol` 卷序列号；相同就是映射，别去查分区/坏道。
2. 定位映射目标用 `QueryDosDeviceW('<盘符>')`，输出直接是 `\??\<真实路径>`。
3. 判断是不是系统级盘符看 `MountedDevices` 里有没有 `\DosDevices\<X>:`；没有就是会话级映射。
4. 删映射前必须 `Get-CimInstance Win32_Process` 查命令行里有没有引用该盘（构建/测试进程常把盘符写进 PATH）。
5. 构建脚本要映射盘符时，必须做"失败也清理"的兜底，否则一次中断就留一个幽灵盘。

## 适用范围与不适用范围

- 适用：Windows 上任何 subst / DefineDosDevice / 虚拟盘工具造成的盘符重复或残留。
- 不适用：真正两块同型号同容量磁盘（卷序列号不同）；网络盘（`net use` 可见）；VHD（`Get-Disk` 可见）。

## 2026-11-08 补：写清理脚本时踩到的两个坑与加固做法

原构建脚本 `构建当前Qt.cmd` 里有个**从来没生效过的判断**：`subst %%D: >nul 2>&1`——
**`subst <盘符>:`（只给盘符、不给路径）在本机不是合法查询**，直接回「无效参数」，
所以它每次都走"该盘空闲"分支；遇到已有残留映射时 `subst` 建映射会失败，于是**换个盘符绕开**，
残留永远清不掉。正确的查询只有**不带任何参数的 `subst` 列全表**。

第二个坑：**`findstr` 匹配含反斜杠的路径不可靠**——
`findstr /I /C:"G:\CodeWeave\.local\prep"` 对明明包含该串的行返回 1（连 `/L` 都不行），
但 `findstr /I "qt"` 又能命中。所以**别用 findstr 比对路径**；改用纯 cmd 字符串比较：
按 `>` 拆出 `=>` 右侧、用 `for /f "tokens=* delims= "` 去掉前导空格，再 `if /I "%%C"=="%QT_PHYSICAL%"`。

顺带两个小坑：`subst` 的输出行里带 `=>`，用 `echo %%L` 输出时 `>` 会被当成重定向，**必须给整行加引号**；
`%~dp0` 的**末尾自带反斜杠**，`if exist "%P%.local\..."` 在 P 为盘根时会拼出 `G:\\.local`。

加固后的形态（已实测）：
- 构建脚本：先列全表认领"上次残留且正指向本 SDK"的盘符并复用（结束时照常删），否则从 Q 开始挑空闲盘符
  → 生成物里的路径固定为 `Q:/`，不会再每次换字母；
- 新增 `工程文件\工具\清理Qt幽灵盘.cmd`：双击即扫全表、删掉指向本 SDK 的映射，找不到就明说；
- `qt_setup_tool_path.bat`（部署生成的）原来写死 `Q:\bin`，改成**从自身位置向上找 `.local\prep\...\bin`**，
  这样从真实中文路径和 `.local` 联接路径两个入口调用都成立（相对 `..\..` 固定层数只对其中一个入口成立）。

验证方式：从真脚本里原样抽取盘符选择段做两个场景（无残留 → 分配 Q；有残留 → 认领复用），
两轮结束后 `subst` 都为空；清理脚本对真实 SDK 映射实测输出 `[clean] ... removed`。

**补：清理脚本必须有"构建中拒绝执行"的守卫。** 我今天就几乎在 `cmake -E env PATH=Q://bin ...` 跑测试时删掉映射。
做法：`tasklist /FI "IMAGENAME eq cmake.exe"`（再加 ninja/ctest/被测 exe）任一命中就打印 [abort] 并 `exit /b 3`，别删。
实测：有假 cmake.exe 在跑时脚本拒绝且映射保留；杀掉后再跑正常删除。
