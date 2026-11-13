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
`admin-fix-worker.ps1` + `run-admin-fix.ps1` + `fix-admin-items.cmd` + `make-admin-cmd.ps1`（Radmin metric 提权修复）、
`clash-inspect.ps1`、`set-unzip-open-default.cmd`

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
