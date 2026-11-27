| `02_项目代码\dsh-preset-switcher` | DSH desktop profile 以 `link:` 引用，node_modules 内 Junction | 移动/改名→预设切换插件失效 |
| `03_备份\archived-cleanup-20261115\node_modules` | 🔴 Junction 指向活体 `D:\DevCache\.dsh\profiles\desktop\node_modules` | 递归删该备份会**穿透删活体依赖**；须先 `rmdir` 拆链接 |
| `脚本库\07_机器修复与clash清理\sync-repo.ps1` | 本仓库双推入口，内置 `git add -A` | 多会话并行时会把**别人的未提交改动**卷进提交（见「日常用法」警告） |
| 根目录临时探针散件（`_*.py` / `_tmp_*` / 并行会话临时文件夹等） | **活跃并行会话**（如 OpenRevo theme.css 排查）正在写 | 属临时探针，**勿动**；会话结束后由其自行清理归位 |

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
