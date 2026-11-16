---
title: "Git 推 GitHub 报 TLS 握手失败：换 SSL 后端只换报错文案，不是修复"
date: 2026-11-02
domain: common
category: "调试与验证"
status: verified
severity: medium
stack: ["git 2.55.0.windows.3", "Windows", "PowerShell"]
tags: ["git", "github", "gitcode", "tls", "schannel", "openssl", "non-fast-forward"]
---

# 问题：Git 推 GitHub 报 TLS 握手失败，换 SSL 后端只换报错文案

> `verified`：两种后端均复现失败、同环境下 gitcode 推送成功，诊断结论已确认。
> GitHub 侧打通方式：**代理路径已实测可用**（2026-11-12 ls-remote、2026-11-13 完整 push；大包被重置时分块推送，见 [[踩坑-GitHub大包推送被重置需分块推送]]）；SSH 路径仍未验证。

## 一句话结论

`schannel: failed to receive handshake` 与切换后的
`error:0A000126:SSL routines::unexpected eof while reading` 是**同一个根因**——
本网络到 github.com 的 HTTPS TLS 握手被中断，与证书、代理配置、账号权限均无关。
`http.sslBackend openssl` 只是把报错文案换了一套，**不构成修复**。

## 触发条件与影响

- 项目或功能：`E:\fullstack-code`，同时挂两个远程（GitHub + gitcode）
- 环境与版本：Windows + Git 2.55.0.windows.3 + PowerShell
- 触发条件：`git push`（默认追踪 `origin` → github.com）
- 影响范围：GitHub 侧完全不可推；gitcode 侧不受影响，可正常推

## 复现步骤

1. 前置条件：仓库 `main` 追踪 `origin/main`（GitHub），有本地待推提交
2. 操作或命令：`git push`
3. 预期结果：推送成功，或至少给出认证类错误
4. 实际结果：`fatal: unable to access '...': schannel: failed to receive handshake, SSL/TLS connection failed`

切换后端后重试：

```bash
git config --global http.sslBackend openssl
git push origin main --dry-run
```

实际结果变为：

```
fatal: unable to access '...': TLS connect error: error:0A000126:SSL routines::unexpected eof while reading
```

## 证据

- 默认后端（schannel）：`schannel: failed to receive handshake, SSL/TLS connection failed`
- 切 openssl 后：`TLS connect error: error:0A000126:SSL routines::unexpected eof while reading`
- 同机同时刻、同一条命令形态推 gitcode：`0497eb5..6ad6160  main -> main` 成功
- `git config http.sslBackend` 原为空（未显式配置，走 Windows 默认 schannel）

## 根因分析

- 已确认的根因：到 github.com 的 443 HTTPS 在 TLS 握手阶段被中断（连接被重置）。
  两种独立 SSL 实现（Windows schannel / OpenSSL）都失败，排除「某个库的证书链问题」。
- 排除过的假设：
  - 账号或凭据问题 —— 报错发生在握手阶段，根本没走到认证
  - 远程地址写错 —— 同一地址在别处可用，且报错是 TLS 层而非 404
  - 证书过期 —— 换 OpenSSL（自带 CA 包）后报错性质不变
- 问题归属：环境或依赖（网络出口限制）

## 最小修复

**没有「配置层」修复。** 可行路径按成本排序：

1. **换远程**（本机已验证）：推同内容的 gitcode / Gitee 镜像，`git push atomgit main`
2. **走代理**：`git config --global http.https://github.com.proxy http://127.0.0.1:<port>`（需已有可用代理）
3. **改 SSH**：`git remote set-url origin git@github.com:<owner>/<repo>.git`，
   若 22 端口也被拦，用 `ssh.github.com:443`

不推荐 `http.sslVerify=false`：它只关校验，握手照样断，无效且降低安全性。

## 验证记录

- [ ] 格式化或静态检查：不适用
- [ ] 类型检查或编译：不适用
- [ ] 单元、集成或端到端测试：不适用
- [ ] 构建：不适用
- [x] 启动或手动回归：`git push atomgit main` 成功（`0497eb5..6ad6160`），
      `git status` 与 `atomgit/main` 零差异；GitHub `--dry-run` 仍失败

## 可复用规则

1. **先分层，再修**：`fatal: unable to access` + `SSL/TLS/handshake/0A000126` ⇒ 网络层；
   `[rejected]` / `non-fast-forward` ⇒ 版本层。两类问题修复手段完全不重叠，
   不要在版本层问题上去调 SSL，反之亦然。
2. **判断「换后端是否真的修好了」**：看报错**性质**是否改变，不要只看有没有报错。
   从 `schannel handshake` 变成 `0A000126 unexpected eof` 属于「同一故障换了文案」。
3. **同一台机器上找一个对照目标**：推另一个远程（gitcode/Gitee）成功，
   即可把故障锁定在「特定主机的网络可达性」，而非本机 Git 配置。
4. **判断「本地是否已上传」，比 SHA，不看 status**：
   `git rev-parse HEAD` 与 `git ls-remote <remote> refs/heads/<branch>` 两个 SHA 相等
   ⇒ 内容逐字节一致（Git 内容寻址，不存在「传了一半」）。
   不要用 `git status` 的 ahead/behind 判断——那是**追踪关系**算出来的，
   换了上游或有多远程时会给误导性数字。
5. **合并是否真的改了内容，看 diff 不看日志**：
   `git diff --stat <合并前> <合并后>` 输出为空 ⇒ 这次合并只补了历史拓扑、**零内容改动**。
   多远程镜像同一份内容时，merge commit 的 SHA 不同但树哈希相同，属于正常现象。

## 适用范围与不适用范围

- 适用：Windows + Git for Windows，推 GitHub 出现 TLS 握手类 `fatal: unable to access`
- 不适用：
  - `Authentication failed` / `403` / `401` —— 那是凭据或权限问题
  - 报错指向具体证书名（如 `unable to get local issuer certificate`）—— 那是 CA 链问题，
    换 `sslBackend` 或补 CA 包可能真的有效
  - Linux/macOS —— 默认即 OpenSSL，无 schannel 这一层

## 剩余风险

- GitHub 同步路径：代理已实测（2026-11-12 ls-remote、2026-11-13 完整 push，FlClash 7890；大包需分块，见 [[踩坑-GitHub大包推送被重置需分块推送]]）；SSH 仍未实测，是否可用取决于出口策略
- `http.sslBackend openssl` 是全局配置，会影响所有仓库的 HTTPS 行为；
  若某些内网站点依赖 Windows 证书库，可能出现新的证书告警

## 补充：Git 传输 TLS 中断但 GitHub API 可用（2026-11-02）

同一时刻、同一网络下出现分层结果：

- `git push origin main` → `TLS connect error: error:0A000126 ... unexpected eof`
- `GET https://api.github.com/repos/<owner>/<repo>` 带 Bearer 令牌 → **200**
- `DELETE /repos/<owner>/<repo>/contents/<path>` 带 `sha + branch + message` → **200**，成功生成一个删除文件的提交

因此当只差单文件增删、而 git 传输层被中断时，可临时走 **GitHub Contents API** 完成一次提交；本次用它删除了误入仓库的 `package-lock.json`，并用 `git/trees?recursive=1` 复核文件数与入口文件。

边界：Contents API 适合**单文件或少量文件**的增删改；完整的多文件提交、分支合并仍应走 git push / GitHub Data API，不能把 API 单文件提交当成完整推送替代。

## 关联

- 相关记录：`踩坑-Gitee仓库401分不清缺凭据还是缺权限且fill探测会回显密钥.md`（凭据类，非本类）
- 相关分类：`03-通用/03-调试与验证`
- 相关代码、命令或文档：`git merge-tree --write-tree A B`（合并预演，不碰工作区，Git ≥ 2.38）
