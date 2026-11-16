---
title: "AtomGit（gitcode.com / atomgit.com）与 GitHub 的差异与国内推送判据"
date: 2026-10-15
domain: common
category: 03-通用/04-工程规范与安全
status: verified
severity: low
stack: [Git, AtomGit, GitHub, Windows]
tags: [代码托管, Git, 网络, 认证, 交付流程]
---

# 问题：仓库托管在 AtomGit 上，和 GitHub 有什么不一样、推送时该按哪套判据

## 一句话结论

AtomGit 是国内平台（开放原子开源基金会联合 CSDN 等推出，GitCode 品牌升级而来），**`gitcode.com` 与 `atomgit.com` 是同一套后端的两个域名**；
对本机而言它和 GitHub 最实际的差别是**网络方向相反**：AtomGit 直连 0.4 s 就通、不需要代理，GitHub 直连常被重置、push 要挂 `127.0.0.1:7897`。

## 触发条件与影响

- 项目或功能：`E:\nodejs` → `https://gitcode.com/zhoujinwei/nodejs.git`（学习 Git 基本操作用）。
- 环境与版本：Win11 28000 + 本机 git；系统代理 `127.0.0.1:7897`（`ProxyEnable=1`）。
- 触发条件：选托管平台、写克隆地址、排查"推不上去/域名是不是挂了"。
- 影响范围：判据用错会把"一次 git 侧超时"当成"域名不通"，也会白白给国内站挂代理。

## 复现步骤

1. 前置条件：本地仓库已 commit、`git branch -vv` 显示 `[origin/main]` 无 ahead。
2. 操作或命令（全部只读）：
   - `GET https://<host>/zhoujinwei/nodejs.git/info/refs?service=git-upload-pack`，host 分别取 `gitcode.com` / `atomgit.com`（空 ProxyHandler 直连）；
   - `git ls-remote --heads https://atomgit.com/zhoujinwei/nodejs.git`（带 `GIT_TERMINAL_PROMPT=0`）。
3. 预期结果：两域名同一后端则返回同一 HEAD。
4. 实际结果：见证据。

## 证据

- 裸 HTTP smart-HTTP 端点：`gitcode.com` **200 / 0.4 s**、`atomgit.com` **200 / 0.4 s**，
  两边首块都是 `# service=git-upload-pack` + 同一个 `91acb3670a63b243e7085b61b1d0f1c28cd2ec0b` → **同一套后端**，克隆地址用哪个域名都行。
- 两个域名首页与仓库页 `<title>` 完全一致（`AtomGit - 全球开发者的开源社区…` / `nodejs - AtomGit`）。
- 但 `git ls-remote` 走 `atomgit.com` 那次 **60 s 超时**，而同一端点裸 HTTP 0.4 s 就通 → **git 侧一次超时判不了域名不通**（凭据助手交互、连接复用等都可能造成，未逐一定位）。
- 推送方向的网络差别（本机既有实测）：GitHub 直连 push 常 `Connection was reset`，要 `git -c http.proxy=http://127.0.0.1:7897 push`；
  AtomGit 国内直连即可，**不要**给它挂代理（挂上反而绕到境外出口）。
- 认证：AtomGit/Gitee 这类非 GCM 内置站要显式 `git config --global credential.https://<host>.provider generic`，
  HTTPS 推送用户名是 handle（`zhoujinwei`）、密码是**访问令牌**；GCM 弹窗默认带出的用户名是 `git config user.name`，两者不一致就会 `Access denied`。
- 该仓库当前状态：本地与远端同为 `91acb36`，`git branch -vv` 已无 `ahead` → 推送链路实测走通。

## 根因分析

- 已确认的根因：品牌演进 —— 2023-09-22 CSDN 与华为云 CodeArts 联合推出 GitCode，其后升级为 AtomGit
  （开放原子开源基金会联合 CSDN 等生态伙伴），于是出现「一个平台、两个域名」。
- 排除过的假设：不是两个独立站点做数据同步（同一 HEAD、同一响应体形状）；不是 CDN 假象（git smart-HTTP 报文一致）。
- 问题归属：环境/平台事实，非代码缺陷。

## 最小修复

选平台按用途走，别混用判据：

| 维度 | AtomGit / GitCode | GitHub |
|---|---|---|
| 网络（本机） | 直连 0.4 s，**不用代理** | 直连常 reset，push 走 `7897` |
| 认证 | 访问令牌当密码 + handle 当用户名；GCM 要显式 `provider generic` | PAT / SSH / 浏览器授权，GCM 内置 provider |
| 域名 | `gitcode.com` 与 `atomgit.com` 同一后端，可互换 | 单一 `github.com` |
| 生态 | AtomCode 云开发与 AI 助手、面向国内的开源镜像与下载量统计 | Actions / Codespaces / Pages / Packages / Copilot，全球可见度与开源项目量级 |

课程作业、国内交付、要稳定快 → AtomGit（或 Gitee）；要让全球看到、参与开源、用 CI 与 Copilot → GitHub。
两边同时用就配两个 remote（`git remote add github …`），分别 push，别用 `git pull` 当"上传"。

## 验证记录

- [x] 只读行为测试：两域名 git smart-HTTP 端点各取一次，HEAD 一致。
- [x] 网页标题对照：两域名首页与仓库页 title 一致。
- [x] 推送链路：该仓库本地与远端 commit 号一致（`ahead` 归零）。
      **2026-10-15 稍后复核**：同一仓库变为匿名 403「The project you were looking for could not be found」、
      网页 404、**带凭据 `git ls-remote` 同样报找不到** → 远端仓库已不存在或已改名/转移，本地 `91acb36` 仍在。
      上面这条证据只在当时成立，别拿它当"现在还在"。
- [ ] 未做：单仓库容量、带宽限制、免费额度、内容审核细则 —— 没查官方页就不写数字。

## 可复用规则

**判"某托管域名是否可用"用不带凭据的 git smart-HTTP 行为测试**（`/info/refs?service=git-upload-pack`），
拿到 `# service=…` 首块即证明链路与仓库存在；`git` 命令侧超时只能证明"这一次 git 没拿到响应"，
要带 `GIT_TERMINAL_PROMPT=0` 重跑一次再下结论。**给国内站挂代理是反向优化**，代理只留给 GitHub 这类出境链路。

## 适用范围与不适用范围

- 适用：本机选择克隆地址、配置 remote、排查推送失败；判断 AtomGit 双域名关系。
- 不适用：GitHub 特有的 Actions/Copilot 能力评估；企业自建 GitLab；平台配额与合规条款（未查证）。

## 剩余风险

AtomGit 双域名同后端是 2026-10-15 的实测，平台后续可能收敛域名或改认证策略；
`git ls-remote` 走 `atomgit.com` 超时的根因未定位，若日后稳定复现需重新评估该域名在 git 协议下的可用性。

## 补充：Gitee 对照（2026-10-15 同日追加）

- 归属：Gitee（码云）是**开源中国 OSCHINA** 旗下平台，与 AtomGit（CSDN 系）是两家。
- 实测网络：匿名 git smart-HTTP 打公开仓库 `https://gitee.com/oschina/git-osc.git/info/refs?service=git-upload-pack`
  → **200 / 1.68 s**（同一时刻 AtomGit 两域名 0.3–0.5 s）。两家都**国内直连可用、不要挂代理**；Gitee 首包明显更慢。
- **判存在性的行为不一样（重要）**：同一个不存在的仓库路径，AtomGit 回 **403 + "could not be found"**、网页回 **404**；
  Gitee 回 **401 `[session-xxxx] Unauthorized`** —— Gitee 对「私有」和「不存在」统一回 401 不暴露差异。
  ⇒ 在 Gitee 上判"仓库在不在"**不能靠匿名 HTTP 状态码**，要用登录后的 API 或网页；在 AtomGit 上可以。
- 服务条款类事实：Gitee Pages 官方口径为「因服务维护调整，暂停提供服务」（2024-05 起多份引用），
  启用前还需**实名认证**；仓库/单文件容量等具体配额数字**本轮未核到官方页，不写**。

## 补充：一台机器同时用 AtomGit + GitHub（2026-10-15 本机实测）

- 凭据互不干扰：Windows 凭据管理器按主机分条存 —— 本机实到有 `git:https://gitcode.com`，
  GitHub 侧走 `credential.https://github.com.helper = gh.exe auth git-credential`（GitHub CLI 已登录 `chicatancau-create`）。
- 全局已配 `credential.https://{gitee,atomgit,gitcode}.provider = generic`（这三家不是 GCM 内置 provider，不声明它会去猜 OAuth）。
- **全局没有任何 `http.proxy`**（实测 `git config --global --list` 过滤 proxy 零命中）→ 推 GitHub 会直连、常被重置；
  正确做法是按 URL 挂代理，别挂全局（否则国内站被绕到境外出口）：
  `git config --global http.https://github.com.proxy http://127.0.0.1:7897`
- 提交本身与平台无关：`add → commit` 只动本地仓库，**只有 `push` 才选目标**；一个工作目录可挂多个 remote，
  用 `git push <remote> <branch>` 区分。身份归属看 `user.email`（本机全局是 `zhoujinwei@noreply.gitcode.com`，
  要让 GitHub 也算给你，得把这个邮箱加进 GitHub 账号，或在仓库里 `--local` 另设）。
- 自查三件套：`git remote -v`、`git branch -vv`（看 `ahead N` = 有 N 个提交没推）、`git log --oneline --decorate`。
- 顺手记一条本机事故判据：练习目录 `E:\nodejs` 于 2026-10-15 11:29 被删，**整目录进了回收站**
  （Shell.Application 枚举到 `nodejs | 原位置=E:\ | 33.9 KB`），含 `.git` 与全部提交，右键还原即可；
  远端同名仓库则已 404，两边要分别恢复。

## 补充：双端一次推送已于 2026-10-15 端到端跑通（`E:\fullstack-code`）

- 配置形态：`origin` 的 `remote.origin.url` 留 GitHub 当 fetch 源，另加两条 `remote.origin.pushurl`
  （**先 AtomGit 后 GitHub**，顺序即推送顺序，一侧挂了另一侧已先落地）。实测 `git push origin main`
  连打两个 `To ...`，两边 HEAD 一致；`git pull` 仍只走 GitHub。
- **按 URL 挂代理这条已实测生效**：GitHub 直连 `Recv failure: Connection was reset`，
  配 `git config --global http.https://github.com.proxy http://127.0.0.1:7897` 后同一条 push 成功，
  且 AtomGit 那一路仍是直连（0.3–0.5 s）。此前"未实测"的标注到此闭环。
- AtomGit 推送时远端回 `remote: Start Git Hooks Checking [PASSED]` —— 是平台侧钩子，不是本地行为，别当报错。
- **同一账号两个命名空间指向同一仓库**：`gitcode.com/zhoumoyukuai/fullstack-code.git` 与
  `gitcode.com/zhoujinwei/fullstack-code.git` 匿名 `ls-remote` 返回**同一个 HEAD**（显示名与 handle 都能用）。
- 覆盖远端历史前留一手：本次 AtomGit 自带一条只含 README 的 `Initial commit`，force push 前记下旧 SHA
  （`b45e643`）再动手，事后要还原有据可依。
- 交付前扫库是硬步骤：这次推公开仓库前对 163 个跟踪文件做了密钥/`.env`/私钥/手机号/身份证/全 0x00 损坏扫描，
  唯一命中是 PNG 二进制里的巧合字节（`C@Dr.Is` 像邮箱）——**误报要认得**，别为此改图。

## 补充：2026-11-12 双账号复核——代理软件已换 FlClash（端口 7897→7890），凭据已恢复且活验通过

- **代理端口漂移（正文里的 7897 已过时）**：本机代理软件现为 **FlClash**（`D:\FlClash\FlClashCore.exe`，实测监听 `:: 7890`；用 `Get-NetTCPConnection -LocalPort 7890` **不加 `-State` 过滤**拿 OwningProcess 定位），**7897 已无任何监听**；系统代理 `ProxyServer=127.0.0.1:7890`（`ProxyEnable=1`）。git 按 URL 代理仍指 7897（死端口）→ 已改 `git config --global http.https://github.com.proxy http://127.0.0.1:7890`，随后 `git ls-remote https://github.com/chicatancau-create/fullstack-code.git`（私有仓库、gh 凭据助手、`GIT_TERMINAL_PROMPT=0`）rc=0 端到端验证通过。**教训：端口随代理软件漂移，用前实测活端口，别照抄正文的 7897。**
- **凭据已恢复且活验通过**：2026-11-02 被 reject 删掉的 `git:https://gitcode.com` 条目已重新存上；gitcode/atomgit 两条都在（UserName=`zhoujinwei`），两条令牌带 Bearer 打 `GET api/v5/user` 均 200、`login=zhoumoyukuai`（同一账号）。方法见 [[03-通用/03-调试与验证/规则-GitCode令牌只读活验用api-v5用户端点]]。
- **配置形态演进**：`E:\fullstack-code` 不再是「双 pushurl」，而是两个独立 remote：`origin`=GitHub、`atomgit`=gitcode，本地 `main` 跟踪 `atomgit/main`；`G:\cc-hud`、`G:\CodeWeave` 同为双 remote 形态。全局 gitee provider 已移除（只剩 gitcode/atomgit 两家）。
- **GitHub 账号活验**：`gh api user -X GET` → `login=chicatancau-create`、`name=zhoumoyukuai`，账号下 7 仓库；探活必须显式 `-X GET`（见 [[03-通用/03-调试与验证/踩坑-ghapi带-f默认POST致探活404误判仓库已删]]）。
- **提交归属已解决（2026-11-12 用户拍板）**：用户确认两个账号绑定的都是 `chicatancau@gmail.com`（m00131：「两个账号的邮箱都绑的是这个」）。GitCode 侧已实证：`GET api/v5/emails` 带 Bearer → 200 `[{"email":"chicatancau@gmail.com","state":"confirmed"}]`；GitHub 侧令牌缺 `user` scope，`GET user/emails` 回 404 查不了邮箱列表，绑定以用户陈述为准。已改 `git config --global user.email chicatancau@gmail.com`（回读确认；`E:\fullstack-code`、`G:\cc-hud`、`G:\CodeWeave` 均无 local 覆盖，全局生效）。**单邮箱即可同时满足两平台归属**——此前「单邮箱无法两全」的判断前提是两账号邮箱不同，用户澄清后不成立。历史提交（`zhoujinwei@noreply.gitcode.com`、CodeWeave 里还有 `zhoumo@users.noreply.local`）在 GitHub 上 `author.login` 均为空、不计贡献；只有新提交计入，改写历史默认不做。

## 补充：2026-11-13 三仓库提交推送完成态与贡献归属验证

- 三仓库全部「本地 HEAD = GitCode = GitHub」（ls-remote 逐一比对，工作区全干净）：
  * `E:\fullstack-code`：5 个新提交（97241b0→4fff672→52894fa→3d040e1→9edcb3d），HEAD=`9edcb3dad85a927f6f5963d0194a05ea239e6998`。
  * `G:\cc-hud`：1 个（9efba67），HEAD=`9efba674397af71ffba0ff8186ca0ea60d320c7d`。
  * `G:\CodeWeave`：67 个（229a411→c83a326），HEAD=`c83a326deb15ac5de7a81739d99c2dc8bfaedc44`；GitHub 单次大包推送中途被重置（curl 56）→ 分块推送成功，见 [[03-通用/03-调试与验证/踩坑-GitHub大包推送被重置需分块推送]]。
- 贡献归属验证命令（显式 GET，带 `-f` 会变 POST）：`gh api repos/<owner>/<repo>/commits?per_page=1 -X GET --jq '.[0].author.login'`（配 `HTTPS_PROXY=http://127.0.0.1:7890`）。实测 fullstack-code 与 CodeWeave 新提交 `author.login=chicatancau-create`、`commit.author.email=chicatancau@gmail.com` → 全局邮箱修改（2026-11-12）生效，新提交两平台都计贡献。
- 旧提交不随推送改变：cc-hud 的 1 个与 CodeWeave 的 66 个旧提交创建于改邮箱前，`author.email` 仍是 `zhoujinwei@noreply.gitcode.com`、`author.login` 为空；不改写历史（双远端 force push 代价大于收益）。
- 提交前审查两坑（全暂存区混入空文件、uploads 样例误判）见 [[03-通用/04-工程规范与安全/踩坑-提交前审查两坑-全暂存区混入空文件与课程样例误判]]。
- 代理 7890（FlClash）已实测可用于 GitHub 大推送（分块）；GitCode 同一批大包可一次推。

## 补充：2026-11-15 网页新建私有仓库并用 GitCode 凭据推送（`G:\cc-hud`）

- 建仓（纯网页，不需要令牌）：工作台 → 新建 → 新建项目；「项目名称」填 `cc-hud` 后「项目路径」手动补同名；「所有者」自动带出 `zhoumoyukuai`；选「私有项目」→「创建项目」。得到 `https://atomgit.com/zhoumoyukuai/cc-hud`。
- 双域名同后端再次实锤：建完立刻打开 `https://gitcode.com/zhoumoyukuai/cc-hud`，看到的是同一个空仓（同标题、同介绍），不需要在 GitCode 侧另建。
- 推送凭据就用已有的那条：本机 `C:\Users\Admin\.gkeys\atomgit.txt` 里 `username=` / `token=` 为空（只有注释），即**没有现成 AtomGit PAT**；但 Windows 凭据管理器已有 `git:https://gitcode.com`（GCM）。因此 remote 故意用 GitCode 域名：
  `git remote add atomgit https://gitcode.com/zhoumoyukuai/cc-hud.git` → `git push -u atomgit main` 一次成功，远端回 `remote: Start Git Hooks Checking [PASSED]`，无弹窗、无需新建令牌。
- 判公开是否生效（零副作用）：`GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote https://atomgit.com/zhoumoyukuai/cc-hud.git` → rc=0 且读到 `refs/heads/main`。**不要用 `git push --dry-run` 探权限**（认证失败会删凭据，见既有记录）。
- 改可见性：仓库页 →「项目设置」（`/setting`）→ 基础设置 →「项目可见性」单选「公开」→ 点该区块的「保存」。页面有两个「保存」（基础信息 / 项目设置），别点错；成功后提示「操作成功」，刷新回读单选仍是公开。
- OpenAPI 形状（**仅查文档，未实调用建仓**）：base `https://web-api.atomgit.com`；建个人仓库 `POST /api/v5/user/repos?access_token=<PAT>`，body `{name, description, private, auto_init, default_branch}`；文档 `https://atomgit-api-doc.atomgit.com/`。该域 `/api/v1/user` 返回 404（与 GitCode 一样只有 v5）。
- 浏览器自动化的具体坑见 [[03-通用/02-AI协作与提示词/经验-Qoder浏览器Agent的evaluate恒null与自绘单选要点label|Qoder 浏览器 Agent 实测要点]]。

## 关联

- 相关记录：[[03-通用/03-调试与验证/踩坑-虚拟网卡空metric抢走默认路由致域名假超时|虚拟网卡空 metric 抢走默认路由致域名假超时]]
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码、命令或文档：`E:\nodejs`（**本地目录已删除**，见正文补充节；历史 `git remote -v` 指向 `https://gitcode.com/zhoujinwei/nodejs.git`）
