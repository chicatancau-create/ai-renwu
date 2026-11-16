---
title: "CC Switch 接入 OpenAI 兼容网关，必须同时满足四件套配置"
date: 2026-11-01
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [cc-switch, OpenAI兼容网关, SQLite, 本地代理]
tags: [判据, 配置, 协议翻译, 路由]
---

# 问题：往 CC Switch 里加一个 OpenAI 兼容的中转，加进去能看见但请求永远打到老供应商 / 404

## 一句话结论

CC Switch（v4.0.4）接入 OpenAI 兼容网关，**四个点必须同时成立**，缺一个就表现为"配了没用"：
`meta.apiFormat = "openai_chat"`、Claude 侧 `isFullUrl=true` 且填完整 URL、
供应商必须 `in_failover_queue=1`、`codexChatReasoning.supportsThinking=false`。

## 触发条件与影响

- 项目或功能：CC Switch 4.0.4 添加自定义供应商，上游只提供 OpenAI Chat Completions（无 Anthropic `/v1/messages`）。
- 环境与版本：Windows 11 + CC Switch v4.0.4（Tauri + WebView2），上游示例 `https://www.workbuddy.ai/v2`。
- 触发条件：手工往 `~\.cc-switch\cc-switch.db` 的 `providers` 表插记录，或按第三方中转的惯例填 `apiFormat=anthropic`。
- 影响范围：供应商在界面里存在、看着正常，但请求静默落到队列里的旧供应商，或稳定 404。

## 复现步骤

1. 前置条件：CC Switch 已开着本地代理 `127.0.0.1:15721`，claude 侧已有若干供应商在故障转移队列里。
2. 操作或命令：写入新供应商 → 把 `live-state.json` 的 `apps.claude.proxy_route` 指向它 → 重启 CC Switch → 打一发 `POST /v1/messages`。
3. 预期结果：请求转发到新上游。
4. 实际结果：日志显示 `[MODE] ... 路由 <新供应商>`（路由确实切了），但紧接着
   `[Claude] >>> 请求目标: <旧供应商域名>`，连续 6 次全部落到旧供应商。

## 证据

- 日志实证（`~\.cc-switch\logs\cc-switch.log`）：
  ```
  [MODE] claude attach：路由 → 路由，路由 workbuddy-claude，客户端配置已重写
  [Claude] >>> 请求目标: https://openox.tech/v1/messages   (1/2)
  [Claude] >>> 请求目标: https://api.aruhub.com/v1/messages (2/2)
  ```
  → 路由字段已改，但实际派发列表来自别处。
- `providers` 表里 `in_failover_queue=1` 的恰好就是那两个旧供应商；把新供应商也置 1 后立刻正常。
- 路径问题：`base_url=https://www.workbuddy.ai/v2` 时日志显示
  `请求目标: https://www.workbuddy.ai/v2/v1/chat/completions` → 直连探测确认该路径 **404**；
  换成完整 URL + `isFullUrl` 后变成 `https://www.workbuddy.ai/v2/chat/completions` → **200**。
- 档位穿透验证：上游对非法 `reasoning_effort` 返回 400（`11133 invalid_parameter_value`）；
  把这个非法值从 CC Switch 代理打过去同样拿到 400 → 证明 `reasoning_effort` 确实被转发。

## 根因分析

- 已确认的根因：
  1. `meta.apiFormat` 的合法枚举是 `anthropic` / `openai_chat` / `openai_responses` / `gemini_native`，
     默认 `anthropic` 是**原样转发**，不会翻译成 OpenAI 协议。
  2. Claude 侧的代理会自己往 base 后拼 `/v1/chat/completions`；上游真实路径不含 `/v1` 时必须用
     `isFullUrl` 写死整条路径。Codex 侧拼的是 `base_url + /chat/completions`，**不要**开 `isFullUrl`。
  3. 代理按 `in_failover_queue=1` 的供应商列表派发；`is_current` 和 `live-state.proxy_route`
     都只是记录/展示，**不决定派发**。
  4. 上游没有 `enable_thinking` 这类开关，`supportsThinking=true` 会发未知字段，被网关直接拒。
- 排除过的假设：以为改 `live-state.json` 就够（实测改了 4 种 `apiFormat` 值 + `is_current` 全改，
  请求照样走旧供应商）；以为 `apiFormat` 值写错导致加载失败（换 `anthropic` 一样走旧供应商）。
- 问题归属：配置理解偏差，非软件缺陷。

## 最小修复

`providers.meta` 按下面写（Claude 侧）：

```json
{
  "apiFormat": "openai_chat",
  "isFullUrl": true,
  "maxOutputTokens": 128000,
  "codexChatReasoning": {
    "supportsThinking": false,
    "supportsEffort": true,
    "thinkingParam": "passthrough",
    "effortParam": "reasoning_effort",
    "effortValueMode": "passthrough",
    "outputFormat": "reasoning_content"
  }
}
```

激活三件套一起做：`is_current=1` + `in_failover_queue=1` + `live-state.apps.<app>.proxy_route=<id>`，
然后**必须重启 CC Switch**（代理配置在启动时缓存，改文件不重启不生效）。

## 验证记录

- [x] Claude 侧端到端：普通流式 200 / 带 `thinking` 200 / 工具调用 200（正确返回 `tool_use` + `input_json_delta`）。
- [x] Codex 侧端到端：普通 200 / 工具 200 / `minimal` 200 / `xhigh` 200 / `/v1/responses` 200。
- [x] 档位穿透：非法 `reasoning_effort` 从代理打过去拿到上游 400 + `11133`。
- [x] 上游约束：非流式请求 400 `11101`（必须 `stream:true`）；`/v2/v1/chat/completions` 404。
- [x] 回滚：`--restore` 后 `is_current` / `in_failover_queue` / `proxy_route` 逐项还原一致。

## 可复用规则

给 CC Switch 加"上游只说 OpenAI 协议"的供应商时，按这个顺序自检：

1. 日志里 `[MODE] ... 路由 X` 只说明**路由字段**改了，不代表请求会走 X；
   要看紧接着的 `>>> 请求目标:` 那行才是真实上游。
2. 请求没走新供应商 → 先查 `in_failover_queue`，别查 `is_current`。
3. `请求目标` 的路径不对 → 用 `isFullUrl` + 完整 URL 覆盖，不要试图靠拼 base 绕过。
4. 验证"某个参数有没有被中间层吞掉"→ **让上游对非法值报错**，看错误能否穿透，
   比对比响应内容/耗时可靠得多（思考字符数这种指标噪声大到无法判读）。

## 适用范围与不适用范围

- 适用：CC Switch 4.x 接任意 OpenAI 兼容中转；同理适用于其它"本地代理 + 供应商列表"形态的切换器
  （思路通用，字段名要重新确认）。
- 不适用：上游本身提供 Anthropic `/v1/messages` 的中转（那种 `apiFormat=anthropic` 直接透传即可，无需翻译）。

## 剩余风险

- Claude 侧**不显示思考块**：上游只回 `reasoning_content`，代理在 Anthropic 方向没转成 `thinking` 块；
  对话与工具调用不受影响，但界面上看不到"思考中"内容。
- 偶发 502「上游连接失败: error sending request」：同机网络瞬时抖动（同一时刻 CC Switch 自身的
  更新检查也报同样错），重试即通，非配置问题。
- 模型定价库里没有自定义模型 id，日志会刷 `[USG-002] 模型定价未找到`，成本统计记 0。

## 关联

- 相关记录：[[踩坑-第三方Claude客户端自带服务商配置切全局路由无效]]（同为"路由切了但请求没走"类，
  那篇是客户端自带服务商库绕过代理，本篇是代理侧派发列表）
- 相关记录：[[规则-自建provider开推理档位要同时写reasoningEfforts与supportsReasoningEffort]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：`~\.cc-switch\logs\cc-switch.log`；`~\.cc-switch\live-state.json`；
  `~\.cc-switch\cc-switch.db` 的 `providers` / `proxy_config` 表
