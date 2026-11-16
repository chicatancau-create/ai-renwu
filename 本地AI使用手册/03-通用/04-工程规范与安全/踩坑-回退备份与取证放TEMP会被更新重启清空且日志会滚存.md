---
title: "把回退备份与取证证据放在 %TEMP%，会被 Windows 更新重启一次性清空；事件日志同样会滚存掉当天的判据"
date: 2026-11-15
domain: common
category: 工程规范与安全
status: verified
severity: high
stack: [Windows 11, Windows Update, 注册表回滚, 取证, 事件日志]
tags: [备份落点, TEMP, 回滚能力, 日志滚存, 存储感知]
---

# 问题：注册表改动已经生效 8 天，回头要回滚时发现 19 份 `.reg` 备份连同 4 份取证日志一起消失

> 2026-11-03 处置、2026-11-11 发现丢失、2026-11-15 复核并回写手册。

## 一句话结论

`%LOCALAPPDATA%\Temp` **不是存储，是易失层**：Windows 更新在 servicing 之后会连回收站一起清掉它，
而且没有任何报错。凡是「以后可能要回滚」的字节（`.reg` 导出、原件副本、manifest）和「只有当天能取到的判据」
（事件日志摘录、命令输出），**当场必须移出 TEMP**，放到随 git 走的目录或非 TEMP 的备份盘；
事件日志本身有上限会滚存，隔几天再回去查同一条事件就查不到了。

## 触发条件与影响

- 项目或功能：本机系统清理任务（电源计划去重、死服务/死 PATH/死卸载记录删除、卷修复）
- 环境与版本：Windows 11 28000；累积更新 KB5132059 + KB5132687
- 触发条件：把 `reg export` 的备份与取证日志放在 `%LOCALAPPDATA%\Temp\regbk\`、`%TEMP%\*.log`，随后系统自行安装累积更新并重启
- 影响范围：19 份注册表 `.reg` 备份 + 4 份取证日志（`maint.log`/`cbs_summary.txt`/`repair.log`/`spotfix.log`）全灭；同一轮里别人会话放在 TEMP 的 6.35 GiB 取证快照也被清空

## 复现步骤

1. 前置条件：`reg export HKLM\...\PowerSchemes %LOCALAPPDATA%\Temp\regbk\x.reg /y` 写入成功，回读文件存在
2. 操作或命令：什么都不做，等 Windows 自行安装累积更新并重启（本机 11-11 14:37:31 触发）
3. 预期结果：备份与日志仍在
4. 实际结果：14:37 后 TEMP 从 **15.21 GiB / 数千文件 → 0.08 GiB / 114 文件**，`regbk` 目录整个消失，
   `ls regbk` 直接 `No such file or directory`；同时六目录回收站全部清空（C 0.10 / H 2.55 GiB → 0）

## 证据

**事发当轮抄下的（TEMP 已没了，只能靠这段文字留档）**

```
14:35:13  Kernel-Power 1074   Service Pack（计划内）        ← Windows Update 发起重启
14:37:31  Kernel-Power 109    Action Power Action Reboot
14:37:52  Microsoft-Windows-NTFS  id=98 ×6  「卷 C/D/E/F/G/H 运行状况良好，无需执行任何操作」
14:38:19  WindowsUpdateClient id=19 「安装成功: 2026-11 累积更新 (KB5132059) (28000.3501)」
14:48:57  WindowsUpdateClient id=43 「开始安装: Defender 安全智能更新 KB2267602」
```

**2026-11-15 复核还能取到的（三件能核，两件已滚存）**

| 判据 | 命令 | 11-15 实测 |
|---|---|---|
| 更新确实装了 | `Get-CimInstance Win32_QuickFixEngineering` | `KB5132059 11/11/2026`、`KB5132687 11/11/2026` ✅ 仍可查 |
| 不是存储感知干的 | `Get-ScheduledTask -TaskName StorageSense \| Get-ScheduledTaskInfo` | `LastRunTime=11/30/1999`、`LastTaskResult=267011`、`State=Ready`（**从未运行过**）✅ |
| 日志已滚存 | `Get-WinEvent @{LogName='Microsoft-Windows-WindowsUpdateClient/Operational';Id=19}` | 返回「**找不到任何与指定的选择条件匹配的事件**」，而 `Get-WinEvent -ListLog` 显示该日志仍有 1597 条、最后写入 11-15 13:49 ❌ 11-11 那批事件已被冲掉 |
| TEMP 现状 | `agent_artifacts.py` | 1.06 GiB / 3743 文件，全是当天新会话产物，11-11 前的东西一个不剩 ❌ |

## 根因分析

- 已确认的根因：**Windows Update servicing 完成后的自动清理**（伴随重启）覆盖了 TEMP + 回收站；
  同时**事件日志有容量上限会滚存**，所以「晚几天再取证」这件事本身不成立。
- 排除过的假设：存储感知（计划任务从未运行，`LastTaskResult=267011`）；本会话自己的删除动作
  （那一轮只删过我自己写的 4 个临时脚本，且时间点在清空之前）。
- 问题归属：**本次修改引入**（备份选址错误在我这边，不是系统坏了）。系统行为是文档化的，
  我没按「TEMP 是易失层」这条基本事实设计。

## 最小修复

1. 备份与取证一律落到**随 git 走的仓库内目录**或专用恢复盘，不进 TEMP。本机现行落点：
   `G:\AIrenwu\01_任务归档\<任务>\02_证据日志\`（仓库白名单外的历史证据快照，规则「不改写、不搬运内部内容」）
   与 `D:\_recover\`。
2. 把这条做成**工具里的硬闸**而不是靠记性：
   `G:\AIrenwu\脚本库\09_机器体检与垃圾扫描\power_schemes.py --backup DIR` 检测到 DIR 在 TEMP/TMP 下直接拒绝执行（返回 3）。
3. 判据要**当场抄成文本**再落盘：`Get-WinEvent`/`powercfg`/`netstat` 一类有时效的输出，取到就写进
   `02_证据日志\`，不要事后重取。
4. 清理垃圾之前先自查一遍：本任务的备份是否在易失层。若在，先搬走再谈删除。

## 验证记录

- [x] 复现：11-11 14:37 前后 TEMP 与回收站的实测数值（见上表与事发当轮摘录）
- [x] 静态检查：`python -m py_compile power_schemes.py zero_fill_scan.py agent_artifacts.py`（重建的三个脚本）
- [x] 工具闸门：`python agent_artifacts.py` 11-15 实测 TEMP 1.06 GiB 且全部为当天新产物，确认 11-11 前的内容不可恢复
- [x] 反查判据：`Win32_QuickFixEngineering` 仍能证明 11-11 装过 KB5132059（不依赖已滚存的日志）
- [ ] 人为制造一次更新重启来复验 TEMP 清空（不执行：会打断本机正在跑的其它工作）
- 说明：`zero_fill_scan.py --full` 的正负对照已在本机临时夹具上跑过（全零文件判为 zero、尾部带数据的判为 has-data），夹具已删除

## 可复用规则

1. **任何要用于回滚的字节，落点必须与 TEMP 无关**：写备份前先问「这个目录会不会被更新/清理工具整目录删掉」，
   TEMP、`%LOCALAPPDATA%\Temp\*`、浏览器下载临时目录、各种 `*.tmp` 都算易失层。
2. **事件日志是限时证据**：需要 `Kernel-Power`、`WindowsUpdateClient`、`NTFS id=98`、`ServiceControl` 这类事件当判据时，
   当轮就把 `TimeCreated + EventID + Properties` 抄成文本存进仓库，隔几天再取会被滚存。
3. **「谁清了 TEMP」按载体分流**：先看 `StorageSense` 计划任务的 `LastTaskResult/LastRunTime`，
   再看 `Win32_QuickFixEngineering` 有没有当天安装的更新；两者都对不上才考虑人为删除或第三方清理器。
4. **别把「我不记得删过」当结论**：本条之所以能定性，是因为我把事发当轮的数值抄下来了（15.21 → 0.08 GiB）。

## 适用范围与不适用范围

- 适用：Windows 上的备份选址、取证时效判断、注册表/服务/驱动类改动的回滚准备。
- 不适用：Linux/macOS 的 `/tmp`（清理策略不同）；也**不能**据此推断「TEMP 里的东西都是垃圾」——
  里面可能有别的会话正在用的活文件，删除仍要遵守「只删本任务产物」。

## 剩余风险

- 具体是哪个进程执行了 TEMP 与回收站的清空，**没有进程级证据（未证实，2026-11-15 复核时已无从补取）**；
  现有证据只能排除存储感知与本会话自身操作。
- 11-03 那批注册表改动（7 条 AMD 死卸载记录、2 个死服务、5 条死 PATH、3 个死协议处理程序）已无本地回滚文件，
  但过去 12 天系统一切正常，且 PATH 等条目可用 `powercfg`/`reg add` 手工重建。
- 事件日志容量仍会在几天内冲掉新判据，本条记录是唯一长期载体。

## 补充：2026-11-15 第二次命中——跨天续接的会话回来清理垃圾时，TEMP 里的取证脚本已经整批没了

- 场景：11-05 晚在 `wofule` uni-app 任务里把分析/生成/取证脚本和截图全落在 `%LOCALAPPDATA%\Temp`
  （`ref_*.py`、`make_*.py`、`measure_*.py`、`my-verify.js`、`ref_phone.png`、`new_icons.png`、`my-verify-1\my-375.png`）。
  会话跨天续接到 11-15，用户要求"处理本会话产生的垃圾"。
- 盘点命令与结果：`os.listdir(r'C:\Users\Admin\AppData\Local\Temp')` 共 **248** 项，
  按关键词 `ref_ / icons_sheet / new_icons / make_ / measure_ / my-verify / myverify` 命中 **0** 项；
  临时浏览器 profile 目录 `myverify-*` 也 0 个。⇒ **垃圾早已被清空，"清理"这一步是空操作**。
- 同期旁证：`curl http://localhost:8080/static/*.png` 全 `000`（HBuilderX 的 dev server 早停了），
  说明这 10 天里机器确实重启/更新过，与本记录 11-11 的清空事件同一条链。
- 唯一存活的东西：落进仓库并被 git 提交的交付件。
  判据 `git show "HEAD:跨平台应用开发/wofule/pages/my/my.vue" | grep -n "border-radius\|nth-child"` 命中，
  `git cat-file -s` 回 2111（CRLF→LF 归一化后），四张 `static/*.png` 已被跟踪。
- **结论扩展（两条）**：
  1. 本记录的规矩第二次被证实，而且新场景是「会话续接后回来做清理」——
     **续接会话时，默认假设 TEMP 里的自己上一轮的东西已经没了**，先盘点再声称"已清理"或"还留着"。
  2. 想在几天后还能复现取证，只有两条路：当场把字节写出 TEMP（本仓库的 `evidence/`、`G:\AIrenwu`），
     或者**把可复现的最小骨架直接抄进手册正文**。本次选了后者，脚本已抄进
     [[01-前端/02-CSS与视觉/经验-PIL自绘图标须统一ink框居中否则contain盒子里视觉不对称-Pillow|PIL 自绘图标那条记录]] 的"最小修复"段。
- 附带纠正一条口头结论：本轮先前给用户的回复里写了"截图在 `...\Temp\my-verify-1\my-375.png`"，
  该路径在 11-15 已经不存在。**引用 TEMP 路径当证据时，要在同一轮里回读一次文件是否还在。**

## 关联

- 相关记录：[[03-通用/03-调试与验证/踩坑-无权限读ProgramData被当成文件不存在致误删服务拆掉内核]]、
  [[03-通用/04-工程规范与安全/规则-清理归档前先反查三类引用]]、
  [[03-通用/03-调试与验证/踩坑-NVMe异常断电致git对象损坏inflate失败只能重建历史]]
- 相关分类：`03-通用/04-工程规范与安全`
- 相关代码、命令或文档：`G:\AIrenwu\脚本库\09_机器体检与垃圾扫描\agent_artifacts.py`（会话产物盘点）、
  同目录 `power_schemes.py`（`--backup` 带 TEMP 拒绝闸）
