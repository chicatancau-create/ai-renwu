---
title: "GitCode 合并 AtomGit 后：repos 接口匿名 400 点名 private-token 头；gitcode.com 直连超时、走 7890 代理才通"
date: 2026-11-25
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: low
stack: [Git, GitCode, AtomGit, GitHub, curl, PowerShell, Windows]
tags: [凭据, API, 代理, 仓库清单, 乱码]
---

# 问题：想扫 GitCode 账号下全部仓库，网页抓不到、匿名 API 报 400、直连还超时

> `needs-review` 表示尚未完成验证；只有复现、定位、修复和验证都完成后，才改为 `verified`。

## 一句话结论

GitCode 与 AtomGit 已合并为同一平台（gitcode.com 网页标题都变成 AtomGit）；扫仓库清单别抓网页（SPA 空壳），
用 **curl 走当轮活口代理（本轮 127.0.0.1:7890）+ `private-token` 请求头 + `GET /api/v5/user/repos?type=all&per_page=100`**。
匿名打 repos 接口得到的 400「Invalid header parameter: private-token, required」是**网关点名缺头**，不是令牌失效。

## 触发条件与影响

- 项目或功能：盘点用户在 GitCode（zhoumoyukuai）与 GitHub（chicatancau-create）两边各有哪些仓库。
- 环境与版本：Win11 + git 2.55 + GCM（凭据管理器存有 `git:https://gitcode.com`）+ gh CLI（keyring 已登录）；2026-11-25 实测。
- 触发条件：① DSH `web_fetch` 抓 gitcode.com 用户页；② 匿名 curl 打 api/v5 repos；③ curl 直连 gitcode.com:443。
- 影响范围：三条路全失败时容易误判「账号没仓库 / 令牌坏了 / 网站挂了」，实际只是入口形状与网络通路变了。

## 复现步骤

1. 前置条件：本机存有 gitcode 凭据；代理软件在跑（端口会漂，先试连）。
2. 操作或命令：
   - `web_fetch https://gitcode.com/user/zhoumoyukuai/repos`；
   - `curl.exe -sS -m 25 "https://gitcode.com/api/v5/users/zhoumoyukuai/repos?type=all&per_page=100"`（直连、匿名）；
   - 同 URL 加 `-x http://127.0.0.1:7897`。
3. 预期结果：拿到仓库 JSON 列表。
4. 实际结果：
   - web_fetch 只回 SPA 空壳，标题「AtomGit - 全球开发者的开源社区,开源代码托管平台」，无任何仓库数据；抓 API 域名则 connect timeout；
   - 直连 curl：`curl: (28) Connection timed out after 25003 milliseconds`；
   - 7897 代理：`curl: (35) schannel: failed to receive handshake` 与 `curl: (7) Failed to connect ... Could not connect to server`（端口已死）。

## 证据

- 匿名经活口代理打 repos 接口 → **HTTP 400**，响应体（Server: elb，带 HWWAFSESID 华为云 WAF cookie）：
  `{"error_code":400,"error_code_name":"UN_KNOW","error_message":"Orchestration error: Invalid header parameter: private-token, required","trace_id":"..."}`
- 带 `private-token: <令牌>` 头（令牌从凭据管理器取，UserName=zhoujinwei，24 字节，**全程未打印**）经 `-x http://127.0.0.1:7890`：
  `GET https://gitcode.com/api/v5/user/repos?type=all&per_page=100&page=1` → **200**，返回全部 7 个仓库，
  字段含 `full_name / private / public / language / default_branch / pushed_at / description`。
- 合并事实（官方口径）：2025-10-28 GitCode 携手开放原子基金会等推动与 AtomGit 深度整合，2025-11 新一代 AtomGit 平台上线，
  账号体系打通、仓库等数据互相同步（来源：gitcode.com/org/gitcode/discussions/11 平台升级公告、docs.gitcode.com 关于我们）。
  本机旁证：`E:\fullstack-code` 的 `atomgit` remote 实际 URL 就是 `https://gitcode.com/zhoumoyukuai/fullstack-code.git`
  ⇒ 旧拓扑把 GitHub/GitCode/AtomGit 误当成多个平台，实际只剩两个平台。
- GitHub 侧当轮 **gh 直连可用（无需代理）**：`gh repo list chicatancau-create --limit 300 --json ...` 与
  `gh api 'user/repos?affiliation=owner,collaborator,organization_member&per_page=100'` 双查一致 = 11 个仓库（4 公开含 1 fork，7 私有）。
- 附带坑 1（PowerShell 吞 jq 引号）：`--jq "... (if .private then \"private\" ...)"` 里嵌的双引号被 PS 剥掉，
  jq 报 `function not defined: private/0`。jq 参数整体用单引号、内部不再嵌双引号（直接输出 `.private` 布尔即可）。
- 附带坑 2（平台侧乱码救不回）：CodeWeave 在 GitCode 的 description 含 U+FFFD 替换符，
  用 gbk/latin1/cp1252 反向 encode→utf-8 decode 全部失败 ⇒ 存储时字节已丢，本地反解无解；简介以 GitHub/本地仓库为准。

## 根因分析

- 已确认的根因：① 合并后 API 网关强制 `private-token` 头（匿名 400 直接点名）；② gitcode.com 网页是 JS SPA，静态抓取无数据；
  ③ 本机到 gitcode.com 直连超时、7897 代理端口已死，当轮活口是 7890（与全局记忆「代理端口会漂」一致）。
- 排除过的假设：令牌失效（带令牌 200，排除）；账号无仓库（user/repos 返回 7 条，排除）；网站整体挂（经 7890 正常，排除）。
- 问题归属：环境或依赖（平台合并改 API 形状 + 本机网络通路漂移），非本次修改引入。

## 最小修复

不改任何配置。取数路线固定为：
1. 试连代理端口定活口（本轮 7890；7897 已死）；
2. 从凭据管理器取 gitcode 令牌（优先 CredReadW 不回显，见关联记录；用 `git credential fill` 必须
   `GCM_INTERACTIVE=never` + `GIT_TERMINAL_PROMPT=0` 且只留内存、只打印长度）；
3. `curl.exe -sS -m 25 -x http://127.0.0.1:<活口> -H "private-token: <令牌>" "https://gitcode.com/api/v5/user/repos?type=all&per_page=100&page=1"`；
4. GitHub 侧用 gh 双查（repo list + affiliation API）互证，防漏协作/组织仓库。

## 验证记录

- [x] 匿名 400、带令牌 200、直连超时、7897 死、7890 通：2026-11-25 全部实跑。
- [x] 两端清单双查互证：GitHub 11 条两法一致；GitCode 7 条（per_page=100 单页取尽）。
- [x] 乱码反解三种编码均实跑失败，确认平台侧已丢字节。
- [ ] 代理活口与 API 头要求会随时间漂：下次先匿名打一次确认形状，再试连端口。

## 可复用规则

扫 GitCode/AtomGit 仓库清单 = **活口代理 + private-token 头 + api/v5/user/repos**；
匿名 400 点名缺头 ≠ 令牌失效，网页 SPA 空壳 ≠ 没有仓库。令牌只留内存绝不回显。
旧推送拓扑按合并事实理解为两平台；新增/改动 remote 仍须点名。

## 适用范围与不适用范围

- 适用：本机盘点/核对 GitCode（=AtomGit）与 GitHub 自有仓库；同类「网页抓不到 + API 400」的托管平台排查思路。
- 不适用：Gitee（另一家账号体系）；令牌照读用 CredReadW 的细则见关联记录，本条不重复。

## 剩余风险

代理端口、API 头要求、gh 直连可达性都是当轮事实，会漂；令牌到期时间 API 不返回。本记录不含任何令牌值。

## 关联

- 写操作续篇：[[规则-两端仓库对齐写操作GitCode增删改UTF8字节body与gh改公开删仓scope]]
- 相关记录：[[规则-GitCode令牌只读活验用api-v5用户端点]]、
  [[踩坑-Gitee仓库401分不清缺凭据还是缺权限且fill探测会回显密钥]]、
  [[03-通用/04-工程规范与安全/规则-AtomGit与GitHub差异与国内推送判据]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：`G:\AIrenwu\脚本库\01_git账号验证\verify_gitcode.py`；官方公告 https://gitcode.com/org/gitcode/discussions/11
