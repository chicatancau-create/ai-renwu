---
title: "两个安装器写同一目录致双版本混装：resources 归后装者，分离要同步注册表与快捷方式全清单"
date: 2026-10-20
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Windows, Electron, 注册表, 快捷方式]
tags: [安装混装, 卸载, 自更新, 归属判据, 启动验证]
---

# 问题：两个版本的软件装进同一个目录，看起来"合一块了"

> 2026-10-20 复现、定位、修复、验证完成；2026-11-15 复核：两安装各自原地自更新到 5.9.3 / 5.9.4 未再混装，分离方案经受住自更新。

## 一句话结论

混装不是软件 bug，是**两次安装选了同一个目录**：后装者的安装器覆盖 `resources\`，先装者只剩一个 exe 外壳；判归属看 `resources\install-manifest.json`，判国内/国际看更新 feed 域名而不是 exe 文件名；分离＝独立目录＋同步卸载键/文件关联/快捷方式全清单，之后自更新不会再混。

## 触发条件与影响

- 项目或功能：Tencent WorkBuddy（国内）与 WorkBuddy AI（国际）两个 Electron 桌面端（各约 195MB 外壳）。
- 环境与版本：Windows；混装时 WorkBuddy.exe=5.8.3、WorkBuddyAI.exe=5.7.6 同在 `D:\WorkBuddyAIgouji`。
- 触发条件：用户把第二个版本安装到第一个版本的目录（安装器不阻止同目录共存）。
- 影响范围：`resources\` 只有一份，归后装者；先装版本的 exe 失去配套资源；卸载键、快捷方式、文件关联全部指向同一目录，卸载任一个都可能伤到另一个。

## 复现步骤

1. 前置条件：目录里同时存在两个产品 exe（`WorkBuddy.exe`、`WorkBuddyAI.exe`）和两个卸载器。
2. 操作或命令：读 `resources\install-manifest.json`；读两 exe 的 VersionInfo；读 HKCU 卸载键与开始菜单 lnk。
3. 预期结果：若真是"一个软件两个名字"，manifest 应同时覆盖两 exe。
4. 实际结果：manifest `appVersion=5.8.3`、`fileCount=112`，文件清单**不含** `WorkBuddyAI.exe` → resources 归 5.8.3；5.7.6 只剩裸外壳。两目录的 `version` 文件同为 `37.10.3-42`（Electron 运行时版本，不能用来判产品）。

## 证据

- 归属：`D:\WorkBuddyAIgouji\resources\install-manifest.json` appVersion=5.8.3、fileCount=112，清单无 WorkBuddyAI.exe。
- 注册表 `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`：`BFD312E9-1019-4F57-9F44-F86246833B50`=WorkBuddy 5.8.3；`C02C88CB-5DAE-4330-AEC1-572CFD048A59`=WorkBuddy AI 5.7.6；两者 UninstallString/DisplayIcon 都指 `D:\WorkBuddyAIgouji`。
- 国内/国际判据：`C:\Users\Admin\.workbuddy\logs\update\update-20261020.log` 的 feed=`https://www.workbuddy.cn/v2/update?platform=workbuddy-win32-x64-user&version=5.8.3`（HTTP 204）→ **名叫 WorkBuddy 的 5.8.3 实为国内源**；数据目录 `C:\Users\Admin\.workbuddy` 与 `C:\Users\Admin\.workbuddy-ai` 各自独立、均活跃。
- 卸载器死路：`Uninstall WorkBuddyAI.exe /currentuser` 弹 GUI 后无任何改动；加 `/S` 静默同样无改动（实测目录/注册表零变化）。
- 启动验证：agent pwsh 里 `Start-Process` 拉起 → 0.4s 内 exit 0、无进程无日志；改 `explorer.exe <exe>` 模拟双击 → 7 进程＋主窗口＋日志 `STARTUP COMPLETE`。已有实例时再拉起 → exit 0 且日志 `gotTheLock=false` / `SingletonLock not acquired`（单实例正常拦截，非故障）。
- 复核（2026-11-15）：`D:\WorkBuddyAI\WorkBuddy.exe`=5.9.3、`D:\WorkBuddyAIguonei\WorkBuddyAI.exe`=5.9.4，各自原地自更新，目录互不含对方 exe，卸载键/lnk 各自正确。

## 根因分析

- 已确认的根因：两次安装目标目录相同；安装器按目录覆盖 resources，不检测目录里已有其他产品。
- 排除过的假设：① "一个软件两个别名"——manifest 清单否定；② exe 文件名/ProductName 判国内国际——update feed 域名否定（WorkBuddy≠国际）；③ 启动 exit 0 是程序坏——explorer 拉起正常＋单实例日志否定；④ SRP/AppLocker 拦截——AppIDSvc Stopped、Paths 规则为空，否定。
- 问题归属：修改前已有（用户安装行为），非软件缺陷、非本次修改引入。
- 未确认（推断，不当结论用）：agent 环境 `Start-Process` 立即 exit 0 的根因未实证，候选解释是执行环境作业对象连带回收（见关联记录）；**验证启动一律走 explorer 拉起＋三重证据，不依赖 Start-Process 的退出码**。

## 最小修复

1. 备份：`reg export` 两个卸载键、目录清单 csv、lnk 副本（本次备份事后已按用户要求清理）。
2. 卸载器不可静默且 GUI 不可操作时手动卸载先装版：删其 exe、其卸载器、其开始菜单 lnk、其 HKCU 卸载键；**数据目录（~/.workbuddy-ai 等）不动**。
3. 整目录 Move-Item 到独立路径（本次最终：国内 `D:\WorkBuddyAI`、国际重装于 `D:\WorkBuddyAIguonei`）。
4. 同步全清单（漏一项就留旧路径死链）：
   - 卸载键 3 值：UninstallString / QuietUninstallString / DisplayIcon；
   - `HKCU\SOFTWARE\Classes\Applications\<exe>\shell\open\command`；
   - 每个 ProgId 的 DefaultIcon 与 `shell\open\command`（WorkBuddy 共 9 个：workbuddy、WorkBuddy.audio/.doc/.html/.image/.md/.pdf/.ppt/.txt/.xls，合计 19 值）；
   - 桌面＋开始菜单 lnk 的 TargetPath/WorkingDirectory/IconLocation。
5. 复扫注册表旧路径字符串＝0 残留；explorer 拉起验证三重证据：进程 Path 分组、主窗口、startup 日志 `STARTUP COMPLETE`。

## 验证记录

- [x] 启动或手动回归：explorer 拉起两版本均 7+ 进程、主窗口、STARTUP COMPLETE（2026-10-20）。
- [x] 注册表复扫：旧路径 0 残留；两卸载键/lnk 各指各自目录（2026-10-20 与 11-15 两次）。
- [x] 冗余检测：两目录互不含对方 exe；同哈希 Electron 运行时文件（icudtl.dat/resources.pak/ffmpeg.dll 等）**不是冗余**，各安装必需；真冗余只有对方残留 exe 与旧 debug.log（crashpad 遗留，已清）。
- [x] 自更新回归：25 天后两安装各自原地更新 5.9.3/5.9.4 未再混装（2026-11-15）。
- [ ] 格式化/类型/单元测试：不适用（系统运维类任务）。

## 可复用规则

1. 判"目录里几个产品"：读 `resources\install-manifest.json` 的 appVersion＋文件清单是否覆盖每个 exe；exe 的 VersionInfo 只代表外壳，`version` 文件只代表 Electron 运行时。
2. 判国内/国际/产品线：看更新日志 feed 域名＋数据目录名（~/.workbuddy vs ~/.workbuddy-ai），**不看 exe 文件名**。
3. 判安装位置三件套：HKCU Uninstall\{GUID} 的 UninstallString/DisplayIcon、开始菜单 lnk TargetPath、数据目录 last-launch.json。
4. 迁移安装目录＝卸载键 3 值＋Applications 关联＋全部 ProgId 两值＋所有 lnk，改完复扫旧路径字符串归零。
5. 卸载器 `/S` 无效且 GUI 不可操作时：reg export 备份后手动删 exe/卸载器/lnk/卸载键/关联键；用户数据目录默认保留。
6. 验证 GUI 程序启动：`explorer.exe <exe>` 模拟双击＋进程 Path 分组＋主窗口＋startup 日志；`Start-Process` 立即 exit 0 不作失败证据；二次拉起 exit 0 先查单实例锁日志再判故障。
7. 防更新再混装：独立目录＋独立卸载键即足够（自更新按各自卸载键/manifest 原地更新）；**唯一复发路径是人再次把安装器指到同一目录**，重装时必须手选独立目录。

## 适用范围与不适用范围

- 适用：Electron/NSIS 类 per-user 安装、resources 单份覆盖式安装器；Windows HKCU 卸载键体系。
- 不适用：per-machine 安装（键在 HKLM，需提权）；安装器自带同目录检测的产品；共享运行时按设计单份的套件（那种"同目录"是设计而非混装）。

## 剩余风险

- 安装器默认路径若仍指向旧混装目录，用户一路下一步会再混装；只能靠安装时手选目录规避。
- agent 环境 Start-Process 立即退出的根因未实证（推断为环境作业回收），换环境后验证方法仍以 explorer＋三重证据为准。

## 关联

- 相关记录：[[踩坑-执行环境Start-Process子进程在工具会话结束时被连带回收]]（explorer 拉起的依据）；[[踩坑-沙箱只放行工作区致写E盘被拒且write会抹掉源码BOM]]（workspace-write 拒 D 盘/HKCU 写＝预期 confinement，需获批升级）。
- 相关分类：03-通用/03-调试与验证。
- 相关命令：`reg export HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{GUID} out.reg`；`explorer.exe <exe路径>`。