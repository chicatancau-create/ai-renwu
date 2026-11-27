`admin-fix-worker.ps1` + `run-admin-fix.ps1` + `fix-admin-items.cmd`（Radmin metric 提权修复；clash 段已退役为**仅报告存在性**）、
`make-admin-cmd.ps1`（v1 生成器，**已加 exit 0 永久停用**：一跑就会把「0 文件就删」危险逻辑写回 .cmd）、
`clash-inspect.ps1`（只读排查；精确 `*verge*`/`*mihomo*` 判存活，FlClash 单独列出；枚举加 Test-Path 护栏防「遍历到父目录」）、`set-unzip-open-default.cmd`、
`clash-cleanup-precheck.ps1` + `clash-cleanup-worker.ps1` + `run-clash-cleanup.ps1`（clash 残留目录：六项引用预检→提权完整枚举→逐文件删除→ItemNotFoundException 判别复核）、
`make-admin-cmd-v2.ps1`（重生成退役版 fix-admin-items.cmd，去掉「0 文件就删」危险逻辑）、
`sync-repo-clash.ps1` + `msg-clash-cleanup.txt`（clash 清理轮增量提交与双推）、
`sync-repo.ps1`（**通用**增量提交+双推：`-MsgFile` 传提交信息，含隐私/体积护栏与双远端 HEAD 比对；**内置出口回退**——2026-11-13 实测 7890 端口活但穿它打 GitHub 报 EOF/TLS 0A000126、直连反而通，故 origin 推送失败时自动用 per-command 覆盖走直连，**不改全局配置、不换地址**）、
`verify-optimizations.ps1` + `msg-retire-autodelete.txt`（退役验证：解析检查+活删除断言+v1 惰性哈希比对；**只数活代码行**，注释里提及 Remove-Item 不算）、
`diag-github-push.ps1`（GitHub 推送失败分层诊断：7890 真实握手 / 监听条目**不加 State 过滤** / 进程身份 / git 与系统代理 / 最小真实请求 / ls-remote；只用纯 fetch，绝不 `push --dry-run`）、
`try-direct-github.ps1`（直连判别 + per-command 出口覆盖完成双推 + 双远端比对 + 全局配置回读）、
`verify-remote-heads.ps1` + `msg-verify-verdict.txt`（**双远端 HEAD 三态校验**，`sync-repo.ps1` 末尾自动调用：有界读取 `http.lowSpeedLimit/lowSpeedTime` + 3 次重试 + 直连回退 + 40 位 hex 校验 + `api.github.com` 交叉核对；判定分 **VERIFIED / UNVERIFIED（读不到，明确不是不一致）/ 真 MISMATCH**，退出码 0/2/1。教训：无界 `ls-remote` 卡 300 秒返回空会误报不一致；PowerShell **函数内 `Write-Output` 会污染返回值**，诊断必须走 `Write-Host`）、
`msg-final-index.txt`（索引补齐的提交信息）、`msg-egress-fallback.txt`（出口回退轮提交信息）、
`restore_from_bin.py`（解析回收站 $I 元数据证明删了什么/何时/从哪，还原技能库/默认窗口所属文件）、
`search_recycle.py`（在回收站搜被清掉的 skill-router/headroom 文件）、
`who_reverted.py`（追查谁在 02:23:48 回退了 D:\Skills\skill-router\router.py；shutil.copy2 保留 mtime，镜像还原是头号嫌疑）、
`msg-organize-20261115.txt` / `msg-organize2-20261115.txt` / `msg-session-cleanup.txt`（归类/会话清理轮提交信息）

### 08_实验与预览 — 实验 / 预览测试
`vslang-probe.ps1` + `02_项目代码/vslang-probe/`（VSLANG A/B 实验夹具与日志）、
`preview-test.ps1` / `preview-fixture-test.ps1` + `02_项目代码/preview-fixture/`（flask 预览最小夹具）

### 09_机器体检与垃圾扫描 — 电源方案 / 全零损坏 / Agent 产物（2026-11-15 重建，原脚本随 %TEMP% 被更新重启清掉）
`power_schemes.py`（电源方案盘点：`powercfg -query` 归一化后 sha256 判重；`--delete` 对微软内建与当前活动方案硬拒绝；
`--backup DIR` 把 `.reg` + 方案名清单导出到 DIR，**DIR 落在 TEMP 直接拒绝**返回 3；背景：Driver Booster 每运行一次多复制一份同名方案）、
`zero_fill_scan.py`（扫「尺寸正常但内容全 `0x00`」的断电后遗症：头 1 MiB + 中点取样先判，`--full` 逐字节确认，
输出严格分「全零 / 疑似 / 有内容 / 读不了」四档，稀疏文件用 `GetCompressedFileSizeW` 单独标；
判据正负对照已在本机临时夹具上跑过）、
`agent_artifacts.py`（各 AI Agent 与工具产物点位：大小 / 文件数 / 静默天数 / 档位「安全·需确认·禁区」，**只报告不删除**；
本机 `DisableLastAccess=1` 所以只看 mtime）
经验记录在手册：`本地AI使用手册\03-通用\03-调试与验证\踩坑-电源计划被驱动更新工具复制成同名方案且FriendlyName是REG_EXPAND_SZ.md`、
`本地AI使用手册\03-通用\04-工程规范与安全\踩坑-回退备份与取证放TEMP会被更新重启清空且日志会滚存.md`

### 10_清理与空间回收 — 回收站 / 临时文件 / 系统日志
`cleanup_round2.ps1`（五段式清理：各盘空间快照 → 回收站（`Clear-RecycleBin` + 直接删 `$RECYCLE.BIN` 残渣，留目录壳）→
临时文件（`%TEMP%` / `Windows\Temp` / CrashDumps）→ `C:\Windows\Logs` → 其它候选（`SoftwareDistribution\Download`、
`C:\$SysReset`、Prefetch、WER）；**默认 `-DryRun` 只盘点，`-Apply` 才真删**，日志落任务目录 `02_证据日志`，
脚本库副本落 `%TEMP%\dsh-cleanup-logs`）、
`survey_junk.ps1`（盘点回收站 / 各垃圾候选 / 各盘现状）、
`inspect_recycle.ps1`（回收站按扩展名、按盘、最大文件、月份分布统计）、
`read_recycle_meta.ps1`（解析 `$I` 元数据还原原始路径：v2 偏移 8=原始大小、24=路径长度、28 起 UTF-16LE）、
`archive_recycle_list.ps1`（**删前存档**：回收站完整清单写成 CSV，删后仍可追溯删了什么；**带 `-Tag` 参数防覆盖历史存档**，
如 `-Tag 20261116_r3` → `回收站清单_删除前_20261116_r3.csv`）、
`analyze_recycle_authored.ps1`（按顶层目录聚合来源，判定哪些可能是用户原创内容、需人工过闸）、
`restore_selected.ps1`（按「原始路径前缀 → 目标根」规则表定向还原，命中后逐个数文件数与字节数校验）、
`system_cleanup_worker.ps1` + `run-system-cleanup.cmd`（**需管理员**的三个系统目录清理：`Windows\Logs` 只删
`.log/.etl/.txt/.cab/.old`、`SoftwareDistribution\Download` 先停 `wuauserv` 再删后重启、`C:\$SysReset`、`MEMORY.DMP`；
`.cmd` 用 `fltmc` 判管理员 + 自我提权护栏 + `choice` 取消档最大数最先判；**默认菜单 [1] 仅盘点**，[2] 才真删；
`Windows\Logs` 里没有 `.evtx`，实测 237 文件 = `.etl` 202 + `.log` 19 + `.json` 11 + `.xml` 5，故只命中 221 个）、
`msg-archive-round3.txt` / `msg-handbook-include.txt`（第三轮归档/手册纳入轮提交信息）
