---
title: "git 按 URL 写死代理端口：端口漂移后 env 覆盖不了它，push 全失败"
date: 2026-11-15
domain: common
category: 03-调试与验证
status: verified
severity: medium
stack: [git, FlClash, Windows, curl]
tags: [git, 代理, 端口漂移, 配置优先级, TLS EOF]
---

# 问题：`HTTPS_PROXY` 明明设对了，git 还是连不上——它读的是写死端口的 per-URL 配置

> 事发 2026-11-11 ~ 11-13，2026-11-15 回写。

## 一句话结论

`git config http.https://github.com.proxy` 这类**按 URL 的代理配置优先级高于 `HTTPS_PROXY` 环境变量**，
端口写死后一旦代理软件换端口/重启，`HTTPS_PROXY=... git push` **完全无效**，
报错还是 `Failed to connect ... via 127.0.0.1`（不显示端口，极易误判）。
必须用 `git -c http.https://github.com.proxy=<新值>` 覆盖，或改配置本身；
而且 `--unset-all` 只清当前文件，**global 那份还在**，要用 `--show-origin` 看来源。

## 触发条件与影响

- 项目或功能：向 GitHub 推送/查询
- 环境与版本：Windows；git（`http.sslbackend openssl`、`http.version HTTP/1.1`）；FlClash 作代理
- 触发条件：配置里写死了 `127.0.0.1:7897`，而代理实际监听 `7890`（或代理已停）
- 影响范围：该 URL 的所有 git 网络操作失败；`ls-remote`、`push`、`fetch` 全中

## 复现步骤

1. 前置条件：`git config --global http.https://github.com.proxy http://127.0.0.1:7897`，代理实际在 7890
2. 操作或命令：
   ```bash
   HTTPS_PROXY=http://127.0.0.1:7890 git ls-remote origin refs/heads/main
   ```
3. 预期结果：走 7890 成功
4. 实际结果：`fatal: unable to access ...: Failed to connect to github.com port 443 via 127.0.0.1 after 2052 ms`
   —— 环境变量被忽略，仍在走 7897

## 证据

**配置来源（实测，两份并存）**：

```
$ git config --show-origin --get-all http.https://github.com.proxy
file:C:/Users/Admin/.gitconfig   http://127.0.0.1:7897     ← global
file:.git/config                 http://127.0.0.1:7890     ← local（后加的）
$ git config --get http.https://github.com.proxy
http://127.0.0.1:7890                                        ← 生效的是 local
```

**端口实测（同一时刻）**：

```
监听端口查询：只有 127.0.0.1:7890（FlClash / FlClashCore 在跑），7897 无监听
curl -x http://127.0.0.1:7890 https://api.github.com → 200，0.73s
curl --noproxy '*' https://github.com              → 200，12.0s（直连慢但通）
```

**覆盖后立刻可用（实测）**：

```bash
git -c http.https://github.com.proxy=http://127.0.0.1:7890 ls-remote origin refs/heads/main
→ 5abe6c3... refs/heads/main      # 成功
```

**代理停掉后反过来要关代理（实测，同一会话内先后出现三种状态）**：

```
状态A 7890 在监听 → 走 7890 成功
状态B 7890/7897 都不监听（FlClash 进程在但没起核心）
      → git -c http.https://github.com.proxy= push origin main   # 空值=不走代理，直连成功
状态C 7890 恢复监听（curl 探活回 403）
      → git -c http.https://github.com.proxy=http://127.0.0.1:7890 push origin main  # 成功
```

**另一层：TLS EOF 换 HTTP/2 有效（实测）**：

```
HTTP/1.1 连推 3 次：TLS connect error: error:0A000126:SSL routines::unexpected eof while reading
git -c http.version=HTTP/2 -c http.postBuffer=1048576000 push → 一次成功
```

## 根因分析

- 已确认的根因：git 的 `http.<url>.proxy` 是**按 URL 的显式配置**，优先于通用环境变量；
  端口写死后与代理实际监听端口脱节。
- 叠加因素：
  - 报错文案 `via 127.0.0.1` **不打印端口**，看不出走的是哪个端口，容易误判成「代理挂了」。
  - `git config --unset-all <key>` 只作用于当前配置文件，global 的同名键仍在，
    于是 `--get-all` 仍返回两条，看着像「没删掉」。
- 排除过的假设：
  - 不是代理进程没跑：`FlClash`/`FlClashCore` 进程在，但**进程在 ≠ 端口在监听**（状态 B 实测）。
  - 不是 GitHub 不可达：同一时刻 `curl` 直连与经代理都能拿 200。
- 问题归属：本机配置 + 代理软件端口漂移，不是 git 缺陷。

## 最小修复

1. **先看生效值与来源**，别只看 `--get`：
   ```bash
   git config --show-origin --get-all http.https://github.com.proxy
   git config --get http.https://github.com.proxy      # 这个才是生效值
   ```
2. **临时覆盖用 `-c`**（不动配置，最安全）：
   ```bash
   git -c http.https://github.com.proxy=http://127.0.0.1:<实测端口> push origin <branch>
   git -c http.https://github.com.proxy= push origin <branch>     # 空值 = 强制直连
   ```
3. **端口必须实测**，不能沿用记忆里的数字：
   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' --max-time 12 -x http://127.0.0.1:<port> https://api.github.com
   ```
   注意 `Get-NetTCPConnection -State Listen` 在本机会**假报端口死**（见关联记录），
   判据以 `curl` 实际能否建连为准。
4. TLS EOF 阵发时加 `-c http.version=HTTP/2` 重试，**不要去改 `sslbackend`**。

## 验证记录

- [x] 优先级复现：设 `HTTPS_PROXY=7890` 仍失败，`-c ...proxy=7890` 立刻成功
- [x] 来源查清：`--show-origin` 显示 global 7897 + local 7890 两份并存
- [x] 三种代理状态都实测过：走 7890 成功 / 关代理直连成功 / 恢复后再走 7890 成功
- [x] HTTP/2 修复 TLS EOF：HTTP/1.1 连续 3 次失败后，HTTP/2 一次成功
- [x] 推送结果独立核验：`gh api .../git/ref/heads/<branch>` 回读 SHA 与本地一致（不只看 push 输出）

## 可复用规则

1. **git 网络失败先查 `http.<url>.proxy` 的生效值**，再查环境变量；
   前者会静默压过后者，且报错不显示端口。
2. **代理端口是易变项**：每次任务实测，别信历史记录里的 7897/7890。
   进程在跑不代表端口在监听。
3. 改配置前先 `--show-origin`；`--unset-all` 不清 global，必要时分别处理。
4. 推送成功的判据是**回读远端 SHA**，不是 push 的返回文案
   （`Everything up-to-date` 也可能出现在实际已同步时）。
5. 私有仓库匿名 API 回 404 是正常现象，**要用带凭据的 `gh api` 核验**，
   别把 404 当成「推送失败/仓库不存在」。

## 适用范围与不适用范围

- 适用：本机 FlClash 等会换端口/会停核心的代理；任何设了 per-URL proxy 的 git 仓库
- 不适用：用 SSH 远端（走 `~/.ssh/config` 的 ProxyCommand，与本条无关，本机未实测）

## 剩余风险

- 本轮未改 global 配置（只加了 local 覆盖），**global 里的 7897 仍在**，
  其他仓库仍会踩同一个坑；要不要统一改由用户决定。
- 代理端口后续仍可能变化，本条记录的端口号只作示例，不可直接套用。

## 关联

- 相关记录：[[踩坑-Git推GitHub报TLS握手失败换SSL后端只改报错]]（同属 GitHub 连接层，那条讲握手）、
  [[踩坑-GitHub大包推送被重置需分块推送]]（大包传输层）、
  [[踩坑-杀软断网修复清零系统代理且StateListen过滤假报端口死]]（判端口别用 -State Listen）、
  [[踩坑-FlClash强杀后停未运行不自动起核心且系统代理悬空致全机断网]]（进程在≠核心在）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码：`E:\OBsidian\全栈工程师学习资料库`（`.git/config` 的 per-URL 代理覆盖）
