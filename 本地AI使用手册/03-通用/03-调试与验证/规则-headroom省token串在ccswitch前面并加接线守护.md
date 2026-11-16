---
title: "headroom 省 token 必须串在 cc-switch 前面，并加接线守护"
date: 2026-11-15
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: high
stack: [headroom-ai, cc-switch, Claude Code, Codex, Windows]
tags: [省token, 代理链路, BASE_URL, 守护, 计划任务]
---

# 规则：headroom 串在 cc-switch 前面，且必须有守护把被改回的 BASE_URL 纠正回来

## 一句话结论

链路是 **Agent → headroom:8787 → cc-switch:15721 → 上游**；
headroom 侧用 `ANTHROPIC_TARGET_API_URL` / `OPENAI_TARGET_API_URL` 指向 15721，
Agent 侧只把 BASE_URL 从 15721 改成 8787。
**cc-switch 每次 attach/detach 都会重写客户端 BASE_URL，把 8787 改回 15721**，
所以必须常驻一个守护纠正，否则 headroom 被静默绕过、不报错、只是不再省 token。

## 触发条件与影响

- 本机 cc-switch 本地代理 `127.0.0.1:15721` 负责供应商/模型路由（摸鱼 CodingPlan 等），
  `.claude\settings.json` 与 `.codex\config.toml` 的 BASE_URL 原本都指它，token 是 `PROXY_MANAGED`。
- **直接按 headroom 默认改 BASE_URL 会绕过 cc-switch**，打断供应商路由 → 必须串联而不是取代。
- 实测回退：`cc-switch.log` `01:55:56 detach → 01:56:04 attach`，两个客户端 BASE_URL 被改回 15721。

## 安装与部署（实测命令，幂等）

```
uv tool install --upgrade "headroom-ai[proxy]"
headroom install apply --preset persistent-task --runtime python --scope user ^
  --providers manual --port 8787 --mode cache --no-rate-limit --no-telemetry ^
  --env HEADROOM_OFFLINE=1 ^
  --env ANTHROPIC_TARGET_API_URL=http://127.0.0.1:15721 ^
  --env OPENAI_TARGET_API_URL=http://127.0.0.1:15721/v1 ^
  --env HEADROOM_TIKTOKEN_LOAD_TIMEOUT_SECONDS=2
```

- **必须 `--providers manual` 且不给 `--target`**，否则 headroom 自己去改 Agent 的 BASE_URL。
  部署后回读 `~\.headroom\deploy\default\manifest.json`，`targets: []` 才算没碰。
- 常驻省 token 必须装 `[proxy]`；**不要装 `[all]` / `[ml]`**（上游 SKILL.md 明令）。
- 输出里出现 `ERROR: Access is denied.` 后跟 `successfully created` **不是失败**（改计划任务被拒，
  但部署本身成功）；同时会警告 `Windows Task Scheduler rejected logged-off recovery;
  using session-scoped health recovery`。
- 本机 `schtasks /create` 一律 `Access is denied`（改 headroom 自建任务和新建都被拒），
  **开机自启只能走启动文件夹**：
  `C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\headroom-autostart.vbs`
  里隐藏窗口跑 `ensure-headroom.ps1` + `wire_guard.py --watch`。
  headroom 自建的 `headroom-default-health` 任务每 5 分钟拉活一次，**只在登录期间有效**。

## 守护规则（`D:\Skills\skill-router\wire_guard.py`）

1. **仅当 `~\.cc-switch\live-state.json` 里该 app `mode=proxy` 且 `attached=true`** 才把 BASE_URL 改回 8787。
2. **`mode=direct` 一律不动**——用户主动直连要尊重，不是故障。
3. 写前必验 `8787 /health` 返回 200，不健康绝不接线（否则把 Agent 打进黑洞）。
4. 写文件带重试 + 原子 replace + 改前备份。20 秒一轮，日志 `D:\AI-Tool-State\wire-guard\guard.log`。
5. 同一循环里连带跑 `skill_shield.py`（技能库自愈）与 `git_backup.py`（10 分钟去抖自动备份）。

```
python D:\Skills\skill-router\ops.py guard        # 看守护 PID + 日志尾；--fix 立刻纠正
python D:\Skills\skill-router\ops.py wire         # 手工接线；unwire 回滚
python D:\Skills\skill-router\ops.py verify       # 两跳真实补全对比
```

## 证据

- 串联后端到端：`POST /v1/messages` 经 8787 → 200，`model=deepseek-v4.1-flash`，`input_tokens=231`；
  **第二次同请求经 8787 只用 14ms**（headroom 语义缓存命中，0 上游 token）。
- Codex 路由：`/v1/responses` 直连 15721=200/1528ms、经 8787=200/2795ms；
  `/v1/chat/completions` 直连=200/2203ms、经 8787=200/3650ms。
- 真实账本（`headroom savings`）：**394,188 / 6,469,913 tokens（6.1%，占新增输入 13.7%），$0.8044，codex 65 calls**。

## 根因分析

- 已确认：cc-switch 的 attach/detach 流程会重写客户端配置文件里的 BASE_URL，这是它的设计行为，不是 bug。
- 排除过的假设：headroom 自身故障（两跳表现完全一致，见下）；网络/代理问题（15721 直连同样症状）。
- 问题归属：环境或依赖（两个工具都要写同一份配置）。

## 可复用规则（判据纪律）

1. **两跳一致地失败 = 上游问题，不是 headroom**，别改 headroom、别回滚接线。
   先看 `~\.headroom\logs\proxy-8787.log` 有没有 `event=outbound_request ... source=passthrough`
   之后就在等 cc-switch。
2. **`/v1/models` 返回 200 不算数**，余额只在真实补全上以 403 露出：
   `INSUFFICIENT_BALANCE ... upstream_status: HTTP 403; cause: Insufficient account balance`，
   随后 cc-switch 熔断，任何模型打 `/v1/responses` 都在 22ms 内返回 503「所有供应商已熔断，无可用渠道」
   ——**熔断期间无法判定换模型是否可用**，别据此下结论。
3. 上游 `moyucccx.top` 会间歇挂起，**超时在两跳之间随机出现**，重试即可。
4. **不要在本会话里改 DSH 自己的 LLM endpoint**——正跑在上面，改错会断自己的连接。
   DSH 也不走 cc-switch（`.dsh` 下是 llm-deepseek/our-free-model/profiles）。

## 适用范围与不适用范围

- 适用：本机 Claude Code / Codex 走 cc-switch 本地代理的场景。
- 不适用：用户把某 app 切成 `mode=direct`（例如 2026-11-15 02:04 把 claude 换成
  `https://api.pateway.ai/v1` 真 key 直连）——**那种情况下该 app 不省 token，是用户选择，不是故障**。

## 剩余风险

- headroom 常驻代理若挂掉，所有改过 BASE_URL 的 Agent 全断；靠 5 分钟健康任务 + 启动项兜底，
  但**注销后健康任务不跑**，重新登录才由启动项拉起。
- `~\.headroom\models.json` 里给 `deepseek-v4.1-flash` 等写的 128000 是 headroom 自己的保守默认值，
  **不是实测窗口**。schema 见 `headroom/providers/anthropic.py:406 _load_custom_model_config()`：
  `{"context_limits": {"<model>": int}, "pricing": {...}}`，可嵌在 `anthropic`/`openai` 键下。

## 关联

- [[踩坑-headroom省量被上游prompt缓存伪造且离线闸挡住ML压缩器]]
- [[规则-CCSwitch接OpenAI兼容网关要四件套配置]]
- [[踩坑-路由熔断红标是历史失败且探针自身会造假故障]]
- [[规则-本机技能默认只开两个由总路由按需读取]]
