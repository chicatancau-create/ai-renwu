# AIrenwu 脚本仓库

G:\AIrenwu（AI 任务工作区）的版本化备份，**双平台私有仓库**，免得日后找不到。

- GitHub：`https://github.com/chicatancau-create/ai-renwu`（私有，remote 名 `origin`）
- GitCode：`https://gitcode.com/zhoumoyukuai/ai-renwu`（私有，remote 名 `gitcode`）
- 提交身份：`chicatancau@gmail.com`（两平台均计入贡献归属）

## 根目录大纲（2026-11-15 第二轮归类后，长期规矩）

**根目录只允许下列 7 类文件夹 + 本 README + .gitignore，不散放任何文件、任何新文件夹。**

| 目录 | 放什么 |
|---|---|
| `01_任务归档/` | 所有 `YYYY-MM-DD_任务名/` 任务文件夹（含历史任务），内部标准分层 `01_报告 / 02_证据日志 / 03_工具脚本 / 04_产物` |
| `02_项目代码/` | 长期维护的项目：`dsh-preset-switcher/` `gemini-pack/` `vslang-probe/` `preview-fixture/` |
| `03_备份/` | 原件备份：`DeskBox-原件备份-*` `_backup/` `_已废弃脚本归档_20261115/` `archived-cleanup-20261115/` `本地AI使用手册-原件备份-20261115/` |
| `04_磁盘与系统/` | `磁盘整理/` `磁盘占用体检/` 等磁盘/系统级盘点 |
| `05_取证扫描/` | `_scan/` 与并行会话的取证/探针散件 |
| `脚本库/` | 可复用脚本与提交信息，按用途分类（见下方索引） |
| `本地AI使用手册/` | 本地 AI 知识库（踩坑记录 / 规则 / 模板），245 文件 / 1.3 MB，**已纳入版本管理** |

**分类导航**（每类目录都有自己的 README 索引，2026-11-19 补齐）：
`01_任务归档\README.md`（50 任务索引）· `02_项目代码\README.md`（4 项目）· `03_备份\README.md`（6 套备份+危险 Junction 警告）· `04_磁盘与系统\README.md` · `05_取证扫描\README.md` · 脚本库索引见本文件下方「脚本索引」。

> **`本地AI使用手册/` 2026-11-16 从 `E:\本地AI使用手册` 迁入工作区根目录**（E 盘当时在做 ACL 修复，
> 不少会话写不进去；原目录已被移走、`E:\本地AI使用手册` 已不存在）。迁入后它成为工作区第 7 类顶层目录，
> 并由 `.gitignore` 显式放行、随本仓库双推备份。**新记录一律写到 `G:\AIrenwu\本地AI使用手册\`，
> 不要再往 E 盘写**；旧文档里出现的 `E:\本地AI使用手册` 路径按本行理解。

> **`02_项目代码/KaihongOS/` 目前未建**：KaihongOS 的安装镜像与 QEMU/VMware 使用文档存放在
> `H:\下载\KaihongOS桌面版（x86）6.1试用版安装镜像包\`（2026-11-15 从回收站抢救还原），属资料、不入库；将来有代码再建目录。

**以后创建任务/人物后的一切产出**：先建 `01_任务归档/YYYY-MM-DD_任务名/`，所有东西按标准分层放进对应子目录，
禁止散落到根目录、桌面、下载目录。可复用脚本沉淀进 `脚本库/<分类>/`。没有合适分类就新建分类文件夹，不许放外面。

**移不动的东西**（用户 2026-11-15 授权）：先停掉占用进程 → 移动/删除 → 恢复进程（计划任务改路径后重启、
链接重建、应用重启）。历史证据快照（`02_证据日志/`、备份、盘点清单）不改写、不搬运内部内容。

脚本内部引用同目录文件用 `$PSScriptRoot`，不写死根目录绝对路径（再搬家不用改代码）。

## 本地AI使用手册联动（2026-11-16 整合）

手册与任务区一体两面：任务区存证据与脚本，手册存可复用结论，双向互链，不孤军奋战。

- **入口**：`本地AI使用手册\首页.md`（Obsidian）；`本地AI使用手册\AGENTS.md` 是手册工作区级规则，DSH 在手册内任务自动加载。
- **开工前检索**：按症状关键词 grep `本地AI使用手册\03-通用`，或经 skill-router 按需读 `D:\Skills\local-ai-handbook\SKILL.md` 症状索引表。
- **完工回写（已授权自动）**：用户 2026-10-13 授权完工自动回写——已验证经验按 `本地AI使用手册\90-模板\问题记录模板.md` 写对应分类（verified），把握不足写 `99-收件箱`（needs-review），汇报中说明写了什么、写到哪里；写入后补分类 README、`03-通用\通用索引.md` 与 SKILL.md 症状表链接。
- **全局触发**：`~/.dsh/AGENTS.md`（≡`D:\DevCache\.dsh\AGENTS.md`）第〇节「默认先查本手册」，2026-11-16 重建（曾缺失）。
- **经验↔脚本互链**：本 README 脚本索引 09/10 节已引用手册记录；手册记录的证据路径指向 `01_任务归档\…\02_证据日志`。
- 联动规则详情：`本地AI使用手册\03-通用\04-工程规范与安全\规则-任务区与手册一体化联动.md`。

## 知识与记忆地图（四库分治，2026-11-19 整理）

工作区融入了「本地 AI 使用手册」和「原 Qoder Agent 的全局记忆」，加上技能库与各应用私有记忆，共 **4 套知识/记忆体系**。它们实体不同、入口不同、触发方式不同、写入纪律不同——**别混为一谈**：

| 库 | 实体位置 | 是什么 | 入口 | 怎么被触发 | 写入纪律 |
|---|---|---|---|---|---|
| ① 本地 AI 使用手册 | `G:\AIrenwu\本地AI使用手册`（工作区内，Obsidian，已入库） | 已验证的工程经验/踩坑/规则/模板 | `首页.md` | AGENTS.md 第〇节 + skill-router→`D:\Skills\local-ai-handbook\SKILL.md` 症状表 | 完工回写（已授权）：verified 写分类、needs-review 写 99-收件箱 |
| ② 全局记忆（原 Qoder Agent） | `D:\Skills\global-memory`（工作区外，125 条，随技能库双远端备份） | 旧 Agent 的全局记忆/用户偏好/任务边界 | `MEMORY.md`（一行一条索引） | AGENTS.md 第〇节之二：动手前先扫索引 | **只追加**新条目+新索引行，不改写/删除已有 |
| ③ 技能库 | `D:\Skills`（工作区外，53 技能） | 可复用任务技能 | `skill-router\SKILL.md` | 默认只常驻 skill-router+headroom，其余按需读 | 经 skill-router 路由，不直接按名加载 |
| ④ 应用私有记忆 | `.memsearch\` `.workbuddy\` `.workbuddy-ai\`（工作区内隐藏目录） | 各应用自己的会话记忆 | 应用自管 | 应用内部 | **不搬不动、不手工改**（隐私/应用状态） |

**调用链（任何工程任务）**：动手前 → AGENTS.md 第〇节查手册 + 第〇节之二扫全局记忆索引 → skill-router 判定用哪个技能 → 干活 → 完工回写手册（已授权）。
- 全局记忆刷新（单向导入 Qoder 新增，no-clobber）：`C:\Users\Admin\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe -X utf8 D:\Skills\global-memory\sync_from_qoder.py`。
- 记忆导入与 6 Agent 接线详情：`01_任务归档\2026-11-19_导入Qoder全局记忆\01_报告\导入与接线报告.md`；规则：`本地AI使用手册\03-通用\02-AI协作与提示词\规则-全机AI共享全局记忆存D盘Skills库并接线各Agent.md`。
- **任务证据**在 `01_任务归档`、**可复用脚本**在 `脚本库`——它们是产出与工具，不是"记忆"，别和上面 4 库混淆。

## 活体依赖与危险点（搬动/删除前必查）

| 对象 | 依赖/危险 | 后果 |
|---|---|---|
| `01_任务归档\2026-10-10_桌面核心脚本\03_工具脚本\watch.py` | 计划任务 **WindowCenter** 运行中（`D:\PyCharm\Python\pythonw.exe`） | 移动/删除→窗口居中失效 |
| `02_项目代码\dsh-preset-switcher` | DSH desktop profile 以 `link:` 引用，node_modules 内 Junction | 移动/改名→预设切换插件失效 |
| `03_备份\archived-cleanup-20261115\node_modules` | 🔴 Junction 指向活体 `D:\DevCache\.dsh\profiles\desktop\node_modules` | 递归删该备份会**穿透删活体依赖**；须先 `rmdir` 拆链接 |
| `脚本库\07_机器修复与clash清理\sync-repo.ps1` | 本仓库双推入口，内置 `git add -A` | 多会话并行时会把**别人的未提交改动**卷进提交（见「日常用法」警告） |
| 根目录 `_t.py` / `_tmp_bundle.js` / `_tmp_openrevo_utf8.txt` | **活跃并行会话**（OpenRevo theme.css 排查）正在写 | 属临时探针，**勿动**；会话结束后由其自行清理 |

## 仓库设计：白名单 .gitignore

工作区里有大量子目录（历史任务、隐私记忆、应用状态、大备份、含密钥/venv/嵌套仓库的项目），
**不能整目录全推**。所以 `.gitignore` 用白名单：默认忽略根目录一切，只显式放行
`脚本库/` + `02_项目代码/` 下四个工具目录 + `本地AI使用手册/` + **各分类目录的直属 README.md**（01/02/03/04/05 的索引，2026-11-19 加，只放行 README 不放行任务内容）。新增任务目录/隐私目录默认不入库；根目录散脚本也不再放行（逼着归类）。

**纳入的工具目录**：`02_项目代码/vslang-probe/`、`02_项目代码/preview-fixture/`、
`02_项目代码/dsh-preset-switcher/`、`02_项目代码/gemini-pack/`（仅构建脚本，排除三个大快照 .md）、
`本地AI使用手册/`（2026-11-16 迁入，已密钥扫描干净后放行）。

**排除**：`.memsearch/` `.workbuddy*/` `.agent-teams/`（隐私/应用状态）、`01_任务归档/`（历史任务）、
`03_备份/`、`02_项目代码/KaihongOS/`、`02_项目代码/gemini-pack/0[012]-*.md`（派生快照）、
`*.log`（运行日志，结论已沉淀进 `本地AI使用手册/`）。

## 脚本索引（按用途，均在 `脚本库/` 下）

### 01_git账号验证 — Git 账号检查 / 验证 / 邮箱修复
| 脚本 | 作用 |
|---|---|
| `git-accounts-check.ps1` | 盘点本机两个 git 账号（config/ssh/cmdkey/gh/GCM） |
| `verify_gitcode.py` | CredReadW 读 GitCode 凭据 + api/v5/user 活验（不回显密钥） |
| `store-git-credential.py` | 把 GitCode/AtomGit 令牌存进 Windows 凭据管理器：getpass 隐藏输入、令牌形状闸门（挡住「把命令当密钥粘贴」）、用户名不留系统账户名默认值（2026-10-15 由会话产物沉淀，原名 `store-atomgit-credential.py`） |
| `check_gitcode_emails.py` | 查 GitCode 账号绑定邮箱（api/v5/emails） |
| `verify-github.ps1` | GitHub 验证初版（**已废弃**，jq 内嵌双引号被 PS5.1 拆参） |
| `verify-github2.ps1` | GitHub 验证（系统代理/进程排查） |
| `verify-final.ps1` / `verify-final2.ps1` | GitHub 账号/仓库最终验证（显式 -X GET） |
| `verify-proxy7890.ps1` | 验证 7890 代理可用 |
| `fix-commit-email.ps1` | 改全局提交邮箱为 chicatancau@gmail.com |
| `verify-attribution.ps1` / `verify-cw-attribution.ps1` | 验证提交归属（author.login） |

### 02_提交推送 — 三仓库提交 / 推送
| 脚本 | 作用 |
|---|---|
| `precheck-commit.ps1` | 提交前预检（远端/进程/并行会话） |
| `commit-fullstack.ps1` | fullstack-code 分 5 次提交 |
| `commit-codeweave.ps1` | CodeWeave 提交 + 推送 |
| `push-cchud.ps1` | cc-hud 双推 |
| `push-cw-chunked.ps1` | CodeWeave 67 提交分块推送（大包被重置的解法） |
| `msg-cw.txt` / `msg-fs-1..5.txt` / `msg-20261115-cleanup-scripts.txt` | 对应提交信息 |

### 03_工作区扫描
`scan-other-issues.ps1`、`scan-sync-lfs.ps1`、`scan-workspace.ps1` / `scan-workspace2.ps1` / `scan-workspace3.ps1`、
`audit_skills_quality.py`（D:\Skills 逐技能质量审计：frontmatter/触发词/死路径/搬迁前旧引用，只读）、
`regen_docs.py`（重生成 D:\Skills\README.md + THIRD_PARTY.md 来源/许可登记，未知来源记 unknown 不臆造）、
`inventory.py`（全量盘点：树状清单+统计+异常候选+Junction/重复检测；`[ROOT] [OUTDIR]` 参数化，2026-11-19 沉淀）、
`structure_review.py`（结构审查：浅层树+任务归档四目录合规+手册全树；读 inventory.py 的 filelist.csv，`[OUTDIR]` 参数化，2026-11-19 沉淀）

### 04_规则审计
`audit-snapshot.ps1`、`audit-probe2.ps1` … `audit-probe8.ps1`（规则审计探针）、
`audit_all.py`（技能路由+省 token 安装的全量只读体检，11 组 57 项；原在「04_规则审计（机器快照）」，2026-11-19 并入本类消除编号撞车）

### 05_建仓预检与密钥扫描
`repo-precheck.ps1`（目录盘点+根部密钥扫描）、`repo-precheck-dirs.ps1`（候选目录扫描）、
`gemini-pack-classify.ps1`（掩码分类）、`gemini-pack-passcontext.ps1`（掩码上下文）、
`probe_provenance.py`（识别真实来源：licence 文本/clawx 元数据/SKILL.md 上游 URL/cc-switch repo_owner 列，不猜）、
`probe_qoder_push.py`（推 QoderToolkit 前：licence+密钥扫描+垃圾检测，13k 文件限定文本跳二进制）、
`scan_handbook_secrets.py`（手册密钥扫描：AWS_AKID/GitHub_PAT/OpenAI_key 等正则）

### 06_建仓与双推
`create-github-repo.ps1`（gh 建 GitHub 私有库）、`create_gitcode_repo.py`（GitCode v5 建私有库）、
`init-and-push.ps1`（init+提交+双推+验证）、`msg-repo.txt`（初始提交信息）、
`fix_byte_fidelity.py`（修 D:\Skills 首次 add 早于 .gitattributes 致 79 文件 CRLF→LF 归一化，按当前属性重暂存使 blob=磁盘字节）、
`gitcode_push.py`（建 GitCode 镜像库并推送，密钥从 Windows 凭据管理器读不回显；`<repo-name> <local-path> [--create-only]`）、
`verify_restore.py`（证明备份真可还原：从各远端 clone 到临时目录逐文件 sha256 比对活体库；"push 成功"不算证据，字节一致还原才算）

### 07_机器修复与clash清理 — 机器修复 / 依赖 / 手册记录移动 / 本仓库同步
`fix-machine.ps1`、`install-flask.ps1`、`move-sandbox.ps1`、`move-vslang.ps1`、
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
实测与判据（2026-11-15）：回收站 52,956 文件 / 21.22 GB 一次清空，全盘合计 +22.42 GB；
`C:\Windows\Logs`、`C:\$SysReset`、`SoftwareDistribution\Download` **非管理员删不掉**，按判据纪律记「失败」不记「已清理」；
还原**目录**必须 `robocopy /E`——`Copy-Item` 不加 `-Recurse` 只建空壳，且目录 `Length` 为 0 会让大小校验误报 PASS。
实测（2026-11-16 第二轮）：回收站又积 8,748 文件 / 2.09 GB → 清空；`%TEMP%` 1,480.8 MB → 73.1 MB；合计 +3.53 GB。
系统目录仍未清（非管理员），改用 `run-system-cleanup.cmd` 双击提权处理，脚本已 DryRun 验证：`Windows\Logs` 可删 221 个 / 27.3 MB。
**坑**：`Get-ChildItem -LiteralPath ... -Recurse -Include *.log` 的 `-Include` **不过滤**（PowerShell 已知行为），
必须改成 `Where-Object { $_.Extension -in '.log', '.etl' }`，否则会连 `.json/.xml` 一起删。

### 工具项目目录（在 `02_项目代码/` 下）
- `dsh-preset-switcher/`：DSH 预设切换器插件（client.js / index.js / 测试；.dsh profile 以 link: 引用，node_modules 内为 Junction）
- `gemini-pack/`：Gemini 双仓数据包构建脚本（`_build_pack.py` 等；快照 .md 不入库）

## 日常用法

> ⚠ **多会话并行警告（2026-11-19）**：`sync-repo.ps1` 内置 `git add -A`，会把**其它会话尚未提交的手册改动**一起卷进提交。
> 多会话共用同一 git 索引时，**改用显式路径暂存**：`git add <只属本会话的路径>` → `git diff --cached --name-only` 核对只含自己的文件 →
> `git commit -F <提交信息>` → `git push gitcode main` + `git push origin main`（失败按 sync-repo 的 per-command 直连回退）→ 跑 `verify-remote-heads.ps1` 校验。
> 单会话、无他人未提交改动时才可直接用 sync-repo.ps1。

```powershell
# 单会话时：新脚本放进 脚本库/<分类>/ 后，用通用同步脚本提交+双推+校验：
powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\07_机器修复与clash清理\sync-repo.ps1 -MsgFile <提交信息文件路径>
# 多会话时手动（显式路径，勿 add -A）：
git add <本会话的文件路径>
git commit -F <提交信息文件>
git push gitcode main   # 国内直连
git push origin main    # GitHub，走本机 7890 出口（git 全局已配代理；失败时 per-command 直连回退）
```

> **Python 解释器**：正主用 DSH 运行时 `C:\Users\Admin\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe -X utf8`（含 numpy/pandas 等）。
> 本机 `D:\PyCharm\Python\python.exe` 的 console exe 于 2026-11-13 发现消失（`pythonw.exe` 仍在，WindowCenter 用它）；
> 备选 uv 的 `C:\Users\Admin\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe`。`python3` 是坏存根，勿用。
> `.ps1` 必须 UTF-8 BOM+CRLF、`.cmd/.bat` GBK 无 BOM（PS5.1 否则按 GBK 解析报错）。
