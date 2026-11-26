---
title: "AppData 缓存迁 D 盘：复用 DSH-Guard 核心按组包装，不引第二套 GUI 迁移工具"
date: 2026-11-24
domain: common
category: "工程规范与安全"
status: verified
severity: medium
stack: ["Windows 11", "NTFS Junction", "Python 3", "PowerShell 5.1"]
tags: ["磁盘迁移", "Junction", "AppData", "DSH-Guard", "防回归", "Viap", "计划任务"]
---

# 问题：C 盘 AppData 越用越大，又怕别的 AI 把已迁数据重复写回 C

## 一句话结论

本机已有验证过的迁移引擎 `D:\DSH-Guard\migrate_dir.py`（逐文件 SHA256 校验、内嵌联接重建、探针验证、失败回滚）和防回归守护 `migrate_guard.py`，**扩到 AppData 只需写薄包装按组切换模块全局变量（HOME/DSTROOT/STATE/ALL/KEEP_ON_C），不要安装第二套 GUI 迁移工具**（本次评估的是 Viap v1.3.3，未安装）。

## 触发条件与影响

- 用户 2026-11-24 要求：检查「之前 AI 把数据从 C 挪到 D 后，是否有 AI 没识别 D 盘数据又把重复数据写回 C」，并把能挪的挪走；工具由 AI 自选（`H:\下载\Viap` 里的 Viap 或手动）。
- 核查结论（先查再动手）：
  - 受守护的 25 个 `C:\Users\Admin\.xxx` 目录**从未回流**（守护日志至 2026-11-24 10:23 反复「正常 25 / 修复 0 / 待处理 0」）。
  - `AppData\Local\uv\cache` 是 **0 MB 空壳**——`UV_CACHE_DIR=D:\dev-cache\uv\cache` 生效，真缓存 2.76 GB 在 D，无重复。
  - `C:\Users\Admin\.cache` 仅 3 MB（codex-runtimes/billion-context/opencode），无 huggingface 重复（`HF_HOME=D:\uv\data\huggingface`）。
  - `AppData\Roaming\npm`（1.43 GB）是**活前缀**（claude/codex/nrm/pi/tokentracker 的 shim），不是陈旧残留；`D:\node-global` 是另一前缀。联接迁移后路径不变，npm 照常工作。
  - 真正没迁的是 AppData 下一批应用数据/缓存（Doubao 3.75G、Postman 1.3G、pnpm store 1.4G、npm-cache 1.1G、Code 1.1G、JetBrains 1G 等）。

## 为什么不用 Viap

Viap（GitHub Chunyu33/viap）是 Junction 重定向 GUI 工具，功能对口，但：本机未安装；GUI 自动化（WebView2）操作风险高于脚本；它会建立**第二套平行迁移历史**，与既有 `migrated.json` + 守护互不相认，日后排查回流要查两套账。既有引擎已接进开机/登录守护，复用成本最低。Viap 文档里「禁迁 UWP/MSIX、Office、浏览器安装目录、GPU 驱动」等红线与本机做法一致，可作选型参考。

## 做法（已验证）

1. **执行器包装** `D:\DSH-Guard\migrate_appdata.py`：`python migrate_appdata.py local|roaming <目录名...>`。两组基目录：
   - local：`C:\Users\Admin\AppData\Local` → `D:\DevCache\AppData-Local`，清单 `migrated_local.json`
   - roaming：`C:\Users\Admin\AppData\Roaming` → `D:\DevCache\AppData-Roaming`，清单 `migrated_roaming.json`
   清单键仍为 `migrated`，与核心 `load_state/save_state` 兼容。核心函数全读模块全局，包装里赋值即切换，**核心脚本零改动**。
2. **守护包装** `D:\DSH-Guard\migrate_guard_appdata.py`：逐组设 `mg.HOME/DSTROOT/STATE`，`mg.ALL = mg.load_state()`（只守护登记者），`mg.KEEP_ON_C = {}`，调 `mg.main()` 取最大退出码。`--quiet/--popup` 透传。
3. **接线**：`guard_on_logon.ps1` 与 `start_dsh.bat` 各加一行调用守护包装（bat 必须纯 ASCII；done 行新增 `appdata=%ARC%`）。
4. **被占用的大目录走开机任务**：模拟器（emulator/qemu/adb）占用 `.android`(4.7G)/`AppData\Local\Android`(4.3G)/`Huawei`(6.6G)，CapCutService 占用 `CapCut`(2.7G)——运行中改名必失败。写 `migrate_emulators.py` 注册计划任务 `EmulatorCacheMigrate`（SYSTEM、AtStartup、2h 上限），开机用户程序未起时迁移，全部成功（或已是联接）后 `schtasks /Delete` 自删。
5. **提权注册**：非提权 `Register-ScheduledTask` 报 `Access is denied (0x80070005)`；按 [[规则-本机管理员提权可静默完成不要推给用户]] 用 `Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -PassThru` 跑 ASCII worker ps1（结果自写日志），注册成功 State=Ready。

## 实际验证结果

- 自检 `D:\AI-Tool-State\disk-audit\selftest_appdata.py`（临时目录，不碰真实数据）：**12/12 PASS**——迁移退出码 0、联接指向正确、内嵌联接重建、清单登记、守护正常态 0、回流自动修复 1（新文件合并进 D）、C 被删重建联接。
- 首批实迁 Doubao：23,117 文件 / 3.66 GB，SHA256 全过，抽样 2000 零异常，联接生效=True（2026-11-24 15:44）。
- Temp 清理（24h 前旧文件）：删 3,848 个，释放 434.8 MB，跳过占用 19 个。
- 批量结果与最终释放量见 `G:\AIrenwu\04_磁盘与系统\磁盘占用体检\本轮清理与迁移记录.md` 2026-11-24 节。

## 踩到的四个小坑

1. `readlink()` 返回带 `\\?\` 前缀的路径，比对联接目标前必须剥掉（守护源码已处理；自测脚本第一版没剥，假 FAIL 一项）。
2. Python stdout 接管道时是块缓冲，`Tee-Object` 日志迟迟不出现——**进度以 `D:\DSH-Guard\migrate_dir.log` 为准**，不是 Tee 日志。
3. `Get-Content` 读 UTF-8 日志要加 `-Encoding UTF8`，否则 PS 5.1 按代码页解码满屏乱码（见 [[踩坑-GetContent默认按代码页解码致UTF8中文回显乱码]]）。
4. **旧副本删不掉的两个真因（都不是文件占用）**：① 超 260 字符路径——JetBrains 共享索引叶子路径约 267 字符（目录名与文件名都含 `sih.org.jetbrains.kotlin.idea.vfilefinder.Kotlin...Index` 长串），PS 5.1 `Remove-Item` 报 `DirectoryNotFoundException`「未能找到路径的一部分」；② 只读属性——Trae CN 的 `ModularData\ai-agent\snapshot\...\.git\objects` 带只读位，`shutil.rmtree` 报 `PermissionError [WinError 5] 拒绝访问`。两例数据均无损（复制走 `\\?\` 长路径，D 侧逐文件核对齐全：JetBrains 4/4、Trae CN 16/16 大小一致）。修复：`D:\DSH-Guard\migrate_dir.py` 第 338/367 行改用 `remove_tree()`，并给 `remove_tree` 加 `_rm_readonly` 处理器（`os.chmod(path, 0o777)` 后重试；3.12+ 用 `onexc`、旧版 `onerror`；**不能与 `ignore_errors=True` 同用，否则处理器不被调用**），三级兜底 rmdir→rmtree→`\\?\` rmtree。教训：删除报错先量路径长度、再看只读位，别误判成进程占用。
5. **DSH 会话继承 `ELECTRON_RUN_AS_NODE=1`，启动 Electron 应用会静默退出**（第二轮 Qoder 重开失败根因）：harness 的 pwsh 子进程带该变量（系统/用户级没有）→ Qoder.exe 进纯 node 模式，无参退出 0、无日志，官方 Launcher 的子进程同样中招。诊断特征：`Qoder.exe --help` 输出 `Usage: node [options]`（正常 Electron 不会）。修复：启动包装器先 `$env:ELECTRON_RUN_AS_NODE=$null` 再 Start-Process（`D:\AI-Tool-State\disk-audit\start_qoder_clean.ps1`），经官方 Launcher（`C:\Users\Admin\AppData\Local\Qoder\Qoder Launcher\Qoder Launcher.exe`）重开成功 ×14。教训：从 agent 会话拉起 GUI Electron 应用一律先清这个变量；「退出 0 无日志」先怀疑 node 模式，别怀疑迁移损坏。
6. **提权进程/服务必须提权关**：非提权 taskkill 杀不掉提权 PowerToys 主进程（目录改名 WinError 32 占用）；非提权 Stop-Service 停不掉 wetype_service（Tencent 改名 WinError 5 拒绝访问）。修复：`Start-Process powershell -Verb RunAs` 静默提权 worker（本机 ConsentPromptBehaviorAdmin=0），提权 taskkill /F + Stop-Service 后迁移，提权应用用 -Verb RunAs 重启（`fix_powertoys_elevated.ps1`/`fix_tencent2_elevated.ps1`）。附带坑：**PS 5.1 按 ANSI 读无 BOM 的 UTF-8 ps1**，脚本内中文正则变乱码永不命中（门控等待空转到超时）→ ps1 内匹配模式用 ASCII。
7. **Python 3.12+（实测 3.15.2）`os.path.islink()` 对 junction 返回 False**：只认 symlink，mount point（reparse tag 0xa0000003）不算；`os.readlink()` 正常（返回带 `\\?\` 前缀）。验证脚本首版用 islink 得 25 个假阴性「不是联接」，而守护用 `md.is_reparse()` 判定全正常。教训：判定联接一律 readlink try/except 或 is_reparse，别用 islink；fsutil reparsepoint query 可权威复核。

## 适用范围与剩余风险

- 适用：本机 ZHOUMO，已有 DSH-Guard 引擎；其它机器要先有同等校验/回滚引擎再谈包装。
- 开机任务已完成：EmulatorCacheMigrate 于 2026-11-24 17:07 重启时执行成功并自删（.android 4.60G / Android 4.16G / Huawei 5.67G / CapCut 0.14G，共 14.57 GB；应用退出后缓存收缩，实际小于日间估算 17.9G）；`.android` 已补进 `migrate_guard.py` 的 ALL 巡检列表。经验：SYSTEM 开机任务先于用户自启服务运行，能抢赢文件锁竞争（CapCutService 自启时迁移已完成）；将来类似任务若失败会回滚并下次开机重试（退出码 2 不自删）。
- 运行中应用数据已于第二轮（2026-11-24 16:10–16:22，用户批准强关）处理：PowerToys/IDM/Qoder×2/Tencent/QQ/QQEX/puccinialin 共 8 目录 8.02 GB，全部重开验证存活；守护清单扩至 local 12 + roaming 13。UWP `Packages`、`Programs`、浏览器用户数据按红线不迁；模拟器/剪映（含鸿蒙 Huawei）留开机任务。
- 给后续 AI 的提醒：`D:\DevCache\AppData-Local|AppData-Roaming` 是 C 盘联接的**真源**，不是重复数据，别「清理」也别再往 C 写副本；全局记忆已登记（reference-appdata-devcache-junctions-2026-11-24、reference-viap-review-and-round2-2026-11-24）。

## 关联

- [[规则-批量搬迁先patch引用后搬与证据快照排除]]
- [[踩坑-删联接目录会跟随联接回收真源须靠回收站元数据取证]]
- [[规则-本机管理员提权可静默完成不要推给用户]]
- 任务区文档：`G:\AIrenwu\04_磁盘与系统\磁盘整理\迁移防回归守护说明.md` 第十一、十二节
- 任务区文档：`G:\AIrenwu\04_磁盘与系统\磁盘整理\Viap-完全使用手册.md`（Viap v1.3.3 完全评审 + 本机 50 联接对照与防误操作）
