---
title: "DSH 启动弹黑框等按键：守卫脚本 pause 叠加遗留中间态目录"
date: 2026-11-20
domain: common
category: "调试与验证"
status: verified
severity: medium
stack: ["Windows", "Python", "cmd", "VBScript", "DeepSeek Harness"]
tags: ["启动守卫", "无窗口启动", "中间态目录", "pause", "wscript"]
---

# 问题：开关 DeepSeek Harness 时弹黑色命令框，停在「请按住任意键继续」，必须按键才能进

## 一句话结论

黑框来自自建的启动守卫 `D:\DSH-Guard\start_dsh.bat`：它用可见的普通 cmd 窗口跑两个 Python 检查，且用 `pause` 阻塞；当天触发条件是 `migrate_guard.py` 修完 `.local` 联接后清理备份目录静默失败，留下 `C:\Users\Admin\.local.__guard_bak`，被自己的「遗留中间态」扫描判为人工待确认项 → 退出码 2 → `pause` 等按键。改成 wscript 隐藏启动 + 去掉 pause + 中间态冗余自愈后，黑框与按键彻底消失。

## 触发条件与影响

- 项目或功能：本机 DeepSeek Harness 桌面版启动链路（开始菜单快捷方式 → 启动守卫 → 主程序）
- 环境与版本：Windows 11 单用户 `C:\Users\Admin`；DSH 内核 0.2.2-rc.5；Python 3.14（`D:\PyCharm\Python\python.exe`）
- 触发条件：守卫任一步退出码为 2（缓存迁移有待处理项 / 内核版本对齐失败）；本例是 `.local` 回流被自动修复后遗留 `.__guard_bak`
- 影响范围：每次开 App 都要手动按键；窗口一直挂着不消失，用户误以为「关软件时又弹一次」。不影响 App 本身运行

## 复现步骤

1. 前置条件：`C:\Users\Admin\.local` 被某个程序重建成实体目录（C 盘回流），`D:\DevCache\.local` 仍有旧数据
2. 操作或命令：点开始菜单「DeepSeek Harness」（指向 `D:\DSH-Guard\start_dsh.bat`）
3. 预期结果：静默检查后直接进 App
4. 实际结果：弹出黑色 cmd 窗口，打印 `[DSH guard] checking cache migration state...`，随后 `[回流] .local ... 已恢复联接 -> D:\DevCache\.local`、`[需处理] 发现遗留中间态目录 .local.__guard_bak（0.00 GB），数据未丢，需确认后再删`、`[WARN] cache migration issue found, see D:\DSH-Guard\migrate_guard.log`、`Press any key to start anyway, or close this window to fix it first.`、`请按住任意键继续。。。`，按键后 App 才启动

## 证据

- `D:\DSH-Guard\migrate_guard.log` 2026-11-20 15:02:23~24 段落：
  - `[回流] .local: 程序把 C 盘路径重建成实体目录，正在合并回 D 盘并恢复联接`
  - `  .local: 已恢复联接 -> D:\DevCache\.local`
  - `[汇总] 正常 24 个 / 自动修复 1 个 / 待处理 1 个`
  - `[需处理] 发现遗留中间态目录 .local.__guard_bak（0.00 GB），数据未丢，需确认后再删`
- 11-15~11-19 每次启动日志只有 `[提示] .headroom: 仍是 C 盘实体目录（0.01 GB），尚未迁移，不影响使用` + `[汇总] 正常 25 个 / 自动修复 0 个 / 待处理 0 个`，退出码 0，因此那些天没有黑框停留（只有一闪而过的窗口）
- `Get-Item C:\Users\Admin\.local` → `LinkType=Junction, Target=D:\DevCache\.local`（联接已恢复）
- `C:\Users\Admin\.local.__guard_bak` 内 3 个文件（`share\opencode\snapshot\<hash>\<hash>\objects\pack\pack-32d4b62ca900300f472c104f894c6b4715d37972.{idx,pack,rev}`，合计 292389 字节）与 `D:\DevCache\.local` 同名同大小且 SHA256 完全一致 → 纯冗余
- 开始菜单快捷方式原始属性：`Target=D:\DSH-Guard\start_dsh.bat`、`WindowStyle=1`（普通窗口，所以黑框可见）

## 根因分析

- 已确认的根因（两层）：
  1. `migrate_guard.py` 的 `migrate_back()` 在重建联接成功后执行 `shutil.rmtree(bak, ignore_errors=True)`，删不掉也不报错，残留 `.__guard_bak`；主流程随后把这个残留当「需人工确认」计入 `problems` → `return 2`
  2. `start_dsh.bat` 对退出码 2 用 `pause` 阻塞，且窗口是可见普通窗口 → 必现「按键才继续」，且该窗口在用户不理会时一直挂着，看起来像「关闭时又弹」
- 排除过的假设：不是 DSH 自身的退出钩子（`D:\DevCache\.dsh\profiles\desktop` 与注册表 Run、计划任务里都没有引用 `DSH-Guard` 的关闭动作）；不是 billion-context/headroom 弹窗
- 问题归属：本次修复引入（`.__guard_bak` 是昨天误删 junction 事故的中间态，被守卫自己的清理逻辑留下）

## 最小修复

1. 冗余中间态移走（备份而非直接删）：`C:\Users\Admin\.local.__guard_bak` → `D:\DSH-Guard\_maintenance\_backup\local.__guard_bak-20261120-1508`（3 个文件，哈希与 D 盘一致）
2. `D:\DSH-Guard\migrate_guard.py` 改变三处：
   - 新增 `file_sha1()` / `tree_manifest()` / `leftover_is_duplicate()` / `rm_tree_retry()`：删除失败重试 6 次（间隔 0.4s），仍失败则挪到 `D:\DSH-Guard\_pending_bak`，绝不把「删不掉」变成「卡启动」
   - `migrate_back()` 里两处 `shutil.rmtree(bak, ignore_errors=True)` 全部换成 `rm_tree_retry()`
   - 中间态扫描改为先判冗余：`*.__moving` / `*.__guard_bak` 若其文件（相对路径 + 大小 + 小文件 SHA256）全部已存在于 `D:\DevCache\<同名>`，直接删除并计入 `repaired`；只有真正无法判定冗余时才计入 `problems`
   - `--popup` 条件从 `(repaired or problems)` 收紧为 `problems`：自动修复只写日志，不打断启动
3. `D:\DSH-Guard\start_dsh.bat` 重写：删掉全部 `pause`；输出全部重定向到 `D:\DSH-Guard\last_launch.log`；`migrate_guard.py` 带 `--popup`（只在有待处理项时弹中文框）；内核对齐失败（rc=2）时先启动 App 再调 `notify.py kernel` 弹框；新增 `DSH_GUARD_NO_LAUNCH=1` 用于只检查不启动；文件保持纯 ASCII（中文都在 py 里）
4. 新增 `D:\DSH-Guard\start_dsh_silent.vbs`：`WScript.Shell.Run "<bat>", 0, False`——隐藏窗口、不等待
5. 新增 `D:\DSH-Guard\notify.py`：中文消息框，代码 `migrate` / `kernel`，写 `D:\DSH-Guard\notify.log`
6. 开始菜单快捷方式改为 `Target=C:\Windows\System32\wscript.exe`、`Arguments="D:\DSH-Guard\start_dsh_silent.vbs"`、`WorkingDirectory=D:\DSH-Guard`、`WindowStyle=7`、图标沿用 `D:\DeepSeek Harness\DeepSeek Harness.exe,0`

## 验证记录

- [x] 格式化或静态检查：`python -m py_compile migrate_guard.py notify.py` 退出码 0
- [x] 类型检查或编译：不涉及
- [x] 单元、集成或端到端测试：
  - 修后跑 `migrate_guard.py` → 退出码 0，日志 `正常 25 个 / 自动修复 0 个 / 待处理 0 个`
  - 干跑 `DSH_GUARD_NO_LAUNCH=1 cmd /c start_dsh.bat` → 退出码 0，`last_launch.log` 末行 `=== done: migrate=0 kernel=0 ===`，内核对齐 `[OK] overrides 11 项与 node_modules 实装全部对齐`
  - 隐藏启动实测：临时 vbs（同一 `sh.Run ...,0,False` 机制，设 `DSH_GUARD_NO_LAUNCH=1`）→ 运行中枚举 cmd/powershell，`MainWindowHandle` 全为 0（无可见控制台窗口），日志确有新条目写入，`DeepSeek Harness` 进程数 8→8（没有误启第二个实例）
  - 冗余自愈对照实验：造 `C:\Users\Admin\guard-heal-test.__guard_bak`（`a.txt`、`sub\b.txt`）与 `D:\DevCache\guard-heal-test` 同名同内容 → 守卫退出码 1，日志 `[清理] guard-heal-test.__guard_bak: 内容与 D:\DevCache\guard-heal-test 完全一致，删除遗留目录`，目录被清掉
  - 反向对照：同样造中间态但 D 盘缺文件（首次测试数据造错）→ 守卫正确报 `[需处理]` + 退出码 2，未误删
- [x] 构建：不涉及
- [x] 启动或手动回归：DSH 本体仍在运行未重启；启动链路的隐藏窗口机制已用等价手段实测（见上）

## 可复用规则

1. 启动守卫、体检脚本一律不得用 `pause` / `ReadKey` 阻塞启动。无控制台场景改成「退出码 + 中文消息框」，并且只在必须人工处理时才弹
2. 要让 App 无窗口启动：写一个 `wscript` 的 vbs，内部 `WScript.Shell.Run "<bat>", 0, False`；快捷方式指向 `wscript.exe`，`WindowStyle` 设 7。副作用是 bat 的输出全丢，所以必须重定向到日志文件
3. 修复类脚本删除临时备份目录时要「重试 + 兜底挪走」；直接用 `shutil.rmtree(..., ignore_errors=True)` 会把删不掉的目录留给下次启动，被自己的遗留物扫描判成「待人工确认」，形成天天弹框
4. 判定中间态目录（`.__guard_bak` / `.__moving`）是否冗余，判据是「相对路径 + 大小 + 小文件 SHA256 全覆盖」，不是「目标目录存在」
5. 验证「真的没窗口」的等价手段：运行中用 `Get-Process cmd,powershell | Select MainWindowHandle`，全 0 即无可见控制台

## 适用范围与不适用范围

- 适用：Windows 上任何用 bat 做前置检查再拉起 GUI 程序的启动器；任何「脚本修完顺手删备份」的自愈逻辑
- 不适用：不经过 bat 的启动方式（直接双击 `DeepSeek Harness.exe`、旧的直接指向 exe 的任务栏固定项）不会触发守卫，也就与本文无关；macOS / Linux 无对应机制

## 剩余风险

- 用户若绕过开始菜单、直接双击 exe 启动，守卫不生效（缓存联接检查、内核版本对齐都不会跑）
- `.headroom` 仍是 C 盘实体目录（0.01 GB），日志每次会留一行「尚未迁移，不影响使用」的提示，不影响启动也不弹窗
- `taskbar` 若存在指向旧 `start_dsh.bat` 的固定项会重新出现黑框；已核查本机开始菜单/桌面上只有一条指向 vbs 的快捷方式

## 关联

- 相关记录：`G:\AIrenwu\本地AI使用手册\99-收件箱\踩坑-临时脚本按环境变量推导清理目录误删C盘用户目录junction.md`（`.local` 回流的来源）、`G:\AIrenwu\本地AI使用手册\03-通用\03-调试与验证\规则-宿主自更新时钉版要用启动守卫按宿主自带版本自动对齐.md`（同一个守卫的内核对齐职责）、`G:\AIrenwu\本地AI使用手册\03-通用\04-工程规范与安全\踩坑-删联接目录会跟随联接回收真源须靠回收站元数据取证.md`
- 相关分类：`G:\AIrenwu\本地AI使用手册\03-通用\03-调试与验证`
- 相关代码、命令或文档：`D:\DSH-Guard\start_dsh.bat`、`D:\DSH-Guard\start_dsh_silent.vbs`、`D:\DSH-Guard\notify.py`、`D:\DSH-Guard\migrate_guard.py`、`D:\DSH-Guard\dsh_kernel_sync.py`、`D:\DSH-Guard\last_launch.log`、备份目录 `D:\DSH-Guard\_maintenance\_backup\20261120-1510`
