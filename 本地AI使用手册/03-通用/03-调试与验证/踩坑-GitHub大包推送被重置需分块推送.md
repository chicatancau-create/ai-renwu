---
title: "GitHub 大包推送中途被重置（curl 56）：分块推送解决，别去动 SSL"
date: 2026-11-13
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [git 2.55.0.windows.5, Windows, PowerShell, FlClash]
tags: [git, github, push, 代理, 分块推送, curl56]
---

# 问题：推 GitHub 的大包传输中途被重置，小请求却正常——分块推送是修复

## 一句话结论

经代理向 GitHub 推大包（几十提交 / 几十 MB）时报 `error: RPC failed; curl 56 Recv failure: Connection was reset`，
而 `ls-remote` 等小请求正常 → **握手与认证都没问题，是大包传输中途被重置**。
这与「TLS 握手失败」记录是**不同层**的故障：换 `sslbackend` 无用；
**分块推送**（把中间提交分段推到同一分支 ref，全程 fast-forward）是本机实测有效的修复。

## 触发条件与影响

- 项目：`G:\CodeWeave`，67 个待推提交（`229a411..c83a326`），含一个 29.59MB 的验收证据提交（195 文件）。
- 环境：git 2.55.0.windows.5 + FlClash 代理 `127.0.0.1:7890`（GitHub 按 URL 挂代理）。
- 触发：`git push origin codex/project-layout-20261106` 一次推全部 67 提交。
- 影响：GitHub 侧推送失败（GitCode 侧同一内容一次推成功）；原样重试大包仍失败。

## 证据（2026-11-13 实测）

- 首推报错（原文）：
  ```
  error: RPC failed; curl 56 Recv failure: Connection was reset
  send-pack: unexpected disconnect while reading sideband packet
  fatal: the remote end hung up unexpectedly
  ```
- **分层证据**：失败后 `git ls-remote origin <branch>` 仍正常返回（旧头 `229a411`）→ DNS/TLS/认证全通，问题在大包传输本身。
- 对照：GitCode 一次推同一批 67 提交成功（`229a411..c83a326`，Hooks PASSED）→ 问题特定于 GitHub 出境代理路径。
- 分块推送：67 提交切 7 段（10×6+7），**全部一次成功**，末尾 `ls-remote` 比对
  `origin = c83a326deb15ac5de7a81739d99c2dc8bfaedc44 = 本地 HEAD`。

## 根因分析

- 已确认：代理路径上单次大包传输被重置（传输层），不是握手层。
- 排除过的假设：TLS 握手失败（ls-remote 能通，报错性质与 schannel/0A000126 记录不同）；凭据（GitCode 同凭据成功、GitHub ls-remote 能通）；SSL 后端（未动任何 SSL 配置，仅分块即修复）。
- 问题归属：网络出口（代理对大流量/长连接的稳定性），非 git 配置缺陷。

## 最小修复

分块推送脚本 `G:\AIrenwu\脚本库\02_提交推送\push-cw-chunked.ps1`，要点：

1. `git rev-list --reverse <base>..HEAD` 取待推提交清单（旧→新）；
2. 按 10 个一段推 `<sha>:refs/heads/<branch>` 到 origin（每段都是 fast-forward）；
3. 每段 2 次重试 + 3s 间隔；失败把段减半（10→5→2→1）从同一起点重试；
4. 单提交仍失败 → FATAL 停止（分块的最小粒度是提交，再拆不动）；
5. 末尾 `ls-remote` 比对远端头 == 本地 HEAD 才算完成。

不改写历史、不 force push、不动 SSL 配置。脚本开头有 git 进程守卫（存在其他 git 进程即拒跑），避免并发推送。

## 验证记录

- [x] 2026-11-13 实跑：67 提交 / 7 段全部一次成功，双远端头比对一致（GitCode 单推 + GitHub 分块）。
- [ ] 未测：单个提交内含超大文件（>100MB）时能否通过——分块拆不开提交，那是另一类问题（LFS / 拆历史）。

## 可复用规则

1. **先分层**：`curl 56 / Recv failure / remote end hung up` + 小请求能通 ⇒ 传输层重置，别去动 SSL/握手层的修法。
2. 分块推送是安全的 fast-forward 手法：推中间 SHA 到分支 ref 等价于分段前进，远端历史保持线性。
3. 段大小 10 是本机经验值，失败减半；国内站同一批大包能一次推，别把出境路径的结论套到国内站。
4. GitHub 单文件 100MB 硬限制与本记录无关：分块解决不了它，报错要单独认。

## 适用范围与不适用范围

- 适用：经代理推 GitHub 大包中途被重置；任何「小请求通、大传输死」的 git 远端。
- 不适用：握手层失败（见 TLS 记录）；认证失败（401/403）；单文件超大（需 LFS）。

## 剩余风险

代理节点质量会变，段大小可能要再降；单提交本身过大时分块无能为力（未实测）。

## 关联

- 相关记录：[[踩坑-Git推GitHub报TLS握手失败换SSL后端只改报错]]（握手层，与本记录不同层）、
  [[03-通用/04-工程规范与安全/规则-AtomGit与GitHub差异与国内推送判据]]
- 相关代码：`G:\AIrenwu\脚本库\02_提交推送\push-cw-chunked.ps1`
