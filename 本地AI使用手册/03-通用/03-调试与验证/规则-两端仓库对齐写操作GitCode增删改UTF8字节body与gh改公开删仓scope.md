---
title: "两端仓库对齐写操作：GitCode 增删改 API 要 UTF-8 字节 body；gh 改公开要 consequences 旗标、删仓要 delete_repo scope；GitHub git 走 7890 代理"
date: 2026-11-25
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [Git, GitCode, AtomGit, GitHub, gh CLI, PowerShell, Windows]
tags: [仓库对齐, API, 可见性, 删仓, 代理, 编码, 多分支]
---

# 问题：把 GitHub 与 GitCode 两端仓库清理对齐（建仓/改简介/改公开/删仓/双推）时的一系列写操作坑

> 本条是 [[踩坑-GitCode合并AtomGit后repos接口要private-token头且直连超时走7890]] 的写操作续篇：那条讲「读清单」，本条讲「增删改 + 可见性 + 双推对齐」。

## 一句话结论

GitCode 写操作（建仓/改简介/改可见性/删仓）全部走 **活口代理 7890 + `private-token` 头 + UTF-8 字节 body**；
gh 改公开必须加 `--accept-visibility-change-consequences`，**删仓需要 `delete_repo` scope（默认 gho_ 令牌没有，非交互无法自授）**；
GitHub 的 git clone/push 直连不稳，挂 `http.proxy=7890` 才稳；多分支仓对齐要看**默认分支 HEAD**而非已推的 feature 分支。

## 触发条件与影响

- 项目或功能：用户要求两端仓库「完全对齐 + 全部公开 + 删 4 个旧仓 + 迁移技能 + 双推更新」。
- 环境：Win11 + git 2.55 + GCM + gh CLI（keyring 登录 chicatancau-create，scopes `gist/read:org/repo/workflow`）；2026-11-25 实测。
- 影响：写操作形状/权限/编码任一不对就静默失败或永久乱码；删仓权限缺口无法绕过。

## 证据与最小修复（逐条实跑）

### A. GitCode 写 API（代理 7890，`private-token` 头，令牌从 `git credential fill` 取、只留内存）

- 建仓：`POST https://gitcode.com/api/v5/user/repos`，body `{name,description,private,auto_init}` → 成功；
  重名 → **422** `"Project with same name or path in this namespace already exists"`。
- 改简介 + 可见性：`PATCH https://gitcode.com/api/v5/repos/zhoumoyukuai/{repo}`，body `{description,private}` → **200**。
- 删仓：`DELETE https://gitcode.com/api/v5/repos/zhoumoyukuai/{repo}` → **204**（本轮删 qoder-toolkit 成功）。
- **编码坑（关键）**：body 必须 `[System.Text.Encoding]::UTF8.GetBytes($json)` + `ContentType 'application/json; charset=utf-8'`；
  直接传字符串 body 会让中文**永久变 `?`**（folia 首次建仓即损坏，后 PATCH 修回）。
  读回须 `$wr.RawContentStream.ToArray()` → `[System.Text.Encoding]::UTF8.GetString`；
  默认按 latin1 显示会 mojibake，但**存储本身正确**，别被显示骗到去反复改。

### B. gh CLI（GitHub）

- 改公开：`gh repo edit <owner>/<repo> --visibility public` **必须加** `--accept-visibility-change-consequences`，
  缺它直接报 `use of --visibility flag requires --accept-visibility-change-consequences flag` 并拒绝（rc=1）。
- 删仓：`gh repo delete <owner>/<repo>` → **HTTP 403** `Must have admin rights to Repository ... needs delete_repo scope`。
  默认 gho_ 令牌 scopes 只有 `gist/read:org/repo/workflow`，**无 delete_repo**；凭据管理器 github.com 凭据同样是 gho_，无 GH_TOKEN/GITHUB_TOKEN 环境变量。
  **非交互无法授予 delete_repo**：需 `gh auth refresh -h github.com -s delete_repo`（浏览器授权一次）或 web UI 手删。属缺权限，按自主原则写进总结一次说清。
- 列仓库：`gh repo list --jq '...'` 在 PowerShell 里参数被拆分报 `accepts at most 1 arg(s), received 2`；
  改 `--json name,visibility,isFork` 后在 PS 里 `ConvertFrom-Json` 解析最稳。

### C. GitHub git 通路

- 直连 clone/push 不稳：报 `curl 56 schannel: server closed abruptly` / `curl 18 transfer closed` / `Recv failure: Connection was reset`。
- 修复：`git -c http.proxy=http://127.0.0.1:7890 -c http.postBuffer=524288000 clone/push ...`；`ls-remote` 直连与代理均通。
- GitCode git 直连正常（国内），双端冗余仍在。

### D. 多分支仓的「默认分支」对齐

- `ls-remote <url> HEAD` 返回的是**默认分支** tip（`--symref` 可见 `ref: refs/heads/main`），可能落后于你刚推的 feature 分支。
- 本轮 CodeWeave：feature 分支 `codex/project-layout-20261106` 两端已对齐 63bc085，但默认分支 `main` GitHub=229a411(11-06) 落后 GitCode=9ff0008(11-25) 70 提交。
- 判快进：`git merge-base --is-ancestor origin/main gitcode/main`（rc=0 即可快进）；`git push origin main` 快进对齐（229a411..9ff0008，无强推）。
- 对齐核验须对**每个仓的 HEAD（默认分支）**两端比对，不能只验 feature 分支。

### E. 提交卫生（librarian/migrator 实测）

- PowerShell 5.1 `Out-File -Encoding utf8` **写 BOM**，污染 commit message 标题（开头不可见字符 `﻿chore:`）；
  用 `UTF8Encoding($false)` 重写消息文件或 `git commit -F` 前 TrimStart BOM；amend 须在 push 前。
- 仓库级 git 身份缺失：`git var GIT_AUTHOR_IDENT` 报 `Author identity unknown`；
  本次 commit 传 `-c user.name=... -c user.email=...`，**不改全局**（避免影响 CodeWeave 主仓等其他会话）。
- ai-skills 自动备份守护 `git_backup.py`（`MIN_INTERVAL=600`）每 10 分钟 `git add -A` 自动提交推送，会抢在手工 commit 前；
  手工提交被抢先时，push 前 `--amend` 修正未推送的本地提交即可（不是改写已推送历史）。

## 验证记录

- [x] GitCode POST/PATCH/DELETE 全实跑（folia 建仓、ai-renwu/cc-hud/fullstack-code/CodeWeave/ai-skills 改公开、qoder-toolkit 删除 204）。
- [x] UTF-8 字节 body 修回 folia 乱码简介，RawContentStream 读回确认正确。
- [x] gh 改公开加 consequences 旗标后 cc-hud/ai-renwu/fullstack-code/ai-skills 全转 PUBLIC。
- [x] gh 删仓 403 复现，确认无 delete_repo 令牌（cmdkey + gh auth status + 环境变量三查）。
- [x] 7 个保留仓 HEAD 两端逐一比对全 ALIGNED（含 CodeWeave main 快进修复）。

## 可复用规则

两端对齐 = 同集合 + 同可见性 + 同默认分支 HEAD。GitCode 写操作 UTF-8 字节 body + charset；
gh 改公开加 consequences 旗标、删仓需 delete_repo（缺则属缺权限，给用户确切授权命令）；
GitHub git 挂 7890 代理；多分支仓验 HEAD 默认分支、用 merge-base 判快进。令牌只留内存绝不回显。

## 适用范围与不适用范围

- 适用：本机 GitHub + GitCode(=AtomGit) 自有仓库的清理/对齐/公开/删仓/双推。
- 不适用：Gitee 等他家；组织仓删仓权限模型可能不同；delete_repo 授权必须用户浏览器同意，无法自动化。

## 剩余风险

代理活口、gh 直连可达性、令牌 scope 都是当轮事实会漂；删仓权限缺口需用户授权后才能补完。本记录不含任何令牌值。

## 后续（2026-11-26）：delete_repo 授权完成，4 仓已删，两端收敛到 7 仓

- **device flow 网络坑**：`github.com` 首页 GET 直连 200，但 `gh auth refresh -h github.com -s delete_repo` 的 `POST https://github.com/login/device/code` **直连超时**（`wsarecv ...->20.247.166.64:443`）。「首页通」≠「OAuth 端点通」，必须 `$env:HTTPS_PROXY='http://127.0.0.1:7890'` 后才取得码。代理端口 `Get-NetTCPConnection` 可能查不到 LISTEN，但 `curl -x 7890` 实测通，以 curl 为准。
- **时序坑**：一次性码约 15 分钟过期，无人点报 `context deadline exceeded`。最优解：先 `ask_user_question` 确认用户「现在就点」再生成码并立刻贴出；后台 job 轮询，授权完成自动通知再删。
- **结果**：用户授权后 scopes 含 `delete_repo`，`gh repo delete chicatancau-create/{name} --yes` 删 mediacrawler-intel-workbench / qoder-toolkit / super-productivity / learning-blog-demo 均 rc=0（删前 mirror 备份验 refs）。GitHub 由 11 仓收敛到 **7 仓全公开**，与 GitCode 7 仓逐仓 HEAD 对齐（ai-skills 2fb8d85 / ai-renwu e63260a / fullstack-code 500d573 / CodeWeave 9ff0008 / fullstack-study-library bd9b546 / cc-hud 9efba67 / folia-major 9a01e78）。
- 详见全局记忆 `reference-gh-delete-repo-device-flow-proxy.md`。

## 关联

- 读清单前篇：[[踩坑-GitCode合并AtomGit后repos接口要private-token头且直连超时走7890]]
- 令牌活验：[[规则-GitCode令牌只读活验用api-v5用户端点]]
- 公开前脱敏：[[03-通用/04-工程规范与安全/规则-仓库公开前脱敏须扫全历史且改证据要重签哈希清单]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]