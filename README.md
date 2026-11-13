# AIrenwu 脚本仓库

G:\AIrenwu（AI 任务工作区）根目录散落脚本与小型工具目录的版本化备份，
**双平台私有仓库**，免得日后找不到。

- GitHub：`https://github.com/chicatancau-create/ai-renwu`（私有，remote 名 `origin`）
- GitCode：`https://gitcode.com/zhoumoyukuai/ai-renwu`（私有，remote 名 `gitcode`）
- 提交身份：`chicatancau@gmail.com`（两平台均计入贡献归属）

## 仓库设计：白名单 .gitignore

工作区里有 44 个子目录（历史任务、隐私记忆、应用状态、大备份、含密钥/venv/嵌套仓库的项目），
**不能整目录全推**。所以 `.gitignore` 用白名单：默认忽略根目录一切，只显式放行
根脚本（`*.ps1 *.py *.cmd *.bat *.txt`）+ 下列工具目录。新增任务目录/隐私目录默认不入库。

**纳入的工具目录**：`vslang-probe/`、`preview-fixture/`、`dsh-preset-switcher/`、
`gemini-pack/`（仅构建脚本，排除三个大快照 .md）。

**排除**：`.memsearch/` `.workbuddy*/` `.agent-teams/`（隐私/应用状态）、`2026-*/`（历史任务）、
`DeskBox-*/` `workbuddy-backup/`(206MB) `磁盘占用体检/`(80MB)、`gemini-pack/0[012]-*.md`（派生快照）、
`*.log`（运行日志，结论已沉淀进 E:\本地AI使用手册）。

## 脚本索引（按用途）

### Git 账号检查 / 验证 / 邮箱修复
| 脚本 | 作用 |
|---|---|
| `git-accounts-check.ps1` | 盘点本机两个 git 账号（config/ssh/cmdkey/gh/GCM） |
| `verify_gitcode.py` | CredReadW 读 GitCode 凭据 + api/v5/user 活验（不回显密钥） |
| `check_gitcode_emails.py` | 查 GitCode 账号绑定邮箱（api/v5/emails） |
| `verify-github.ps1` | GitHub 验证初版（**已废弃**，jq 内嵌双引号被 PS5.1 拆参） |
| `verify-github2.ps1` | GitHub 验证（系统代理/进程排查） |
| `verify-final.ps1` / `verify-final2.ps1` | GitHub 账号/仓库最终验证（显式 -X GET） |
| `verify-proxy7890.ps1` | 验证 7890 代理可用 |
| `fix-commit-email.ps1` | 改全局提交邮箱为 chicatancau@gmail.com |
| `verify-attribution.ps1` / `verify-cw-attribution.ps1` | 验证提交归属（author.login） |

### 三仓库提交 / 推送
| 脚本 | 作用 |
|---|---|
| `precheck-commit.ps1` | 提交前预检（远端/进程/并行会话） |
| `commit-fullstack.ps1` | fullstack-code 分 5 次提交 |
| `commit-codeweave.ps1` | CodeWeave 提交 + 推送 |
| `push-cchud.ps1` | cc-hud 双推 |
| `push-cw-chunked.ps1` | CodeWeave 67 提交分块推送（大包被重置的解法） |
| `msg-cw.txt` / `msg-fs-1..5.txt` | 对应提交信息 |

### 工作区扫描
`scan-other-issues.ps1`、`scan-sync-lfs.ps1`、`scan-workspace.ps1` / `scan-workspace2.ps1` / `scan-workspace3.ps1`

### 规则审计（机器快照）
`audit-snapshot.ps1`、`audit-probe2.ps1` … `audit-probe8.ps1`

### 本仓库建仓预检 / 密钥扫描
`repo-precheck.ps1`（目录盘点+根部密钥扫描）、`repo-precheck-dirs.ps1`（候选目录扫描）、
`gemini-pack-classify.ps1`（掩码分类）、`gemini-pack-passcontext.ps1`（掩码上下文）

### 建仓与双推
`create-github-repo.ps1`（gh 建 GitHub 私有库）、`create_gitcode_repo.py`（GitCode v5 建私有库）、
`init-and-push.ps1`（init+提交+双推+验证）、`msg-repo.txt`（初始提交信息）

### 机器修复 / 依赖 / 手册记录移动
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
`msg-final-index.txt`（本索引补齐的提交信息）

### 实验 / 预览测试
`vslang-probe.ps1` + `vslang-probe/`（VSLANG A/B 实验夹具与日志）、
`preview-test.ps1` / `preview-fixture-test.ps1` + `preview-fixture/`（flask 预览最小夹具）

### 工具项目目录
- `dsh-preset-switcher/`：DSH 预设切换器插件（client.js / index.js / 测试）
- `gemini-pack/`：Gemini 双仓数据包构建脚本（`_build_pack.py` 等；快照 .md 不入库）

## 日常用法

```powershell
# 在工作区根目录新增脚本后：
git add -A
git commit -m "说明"
git push gitcode main   # 国内直连
git push origin main    # GitHub，走本机 7890 出口（git 全局已配代理）
```

> 注：本机 `D:\PyCharm\Python\python.exe` 的 console exe 于 2026-11-13 发现消失，
> 运行 .py 可改用 uv 的 `C:\Users\Admin\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe`。
