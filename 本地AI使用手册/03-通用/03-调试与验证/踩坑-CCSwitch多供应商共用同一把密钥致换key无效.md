---
title: "换掉 API 密钥仍然报「密钥无效」：CC Switch 里多个供应商共用同一把 key，改一个等于没改"
date: 2026-11-15
domain: common
category: 调试与验证
status: verified
severity: high
stack: [CC Switch, DeepSeek Harness, Anthropic Messages API, 凭据文件]
tags: [API密钥无效, 共用密钥, CC Switch, credentials.yaml, x-api-key, 401判据]
---

# 问题：在 CC Switch 里给「超算互联网」填了 key，DSH 仍然报 `API 密钥无效 AUTH`

## 一句话结论

不是端点错、不是头错、也不是 DSH 缓存——**四个供应商里有两条 `apiKeyEnv` 指向的密钥值逐字节相同**，
用户把「阿里云百炼」的 key 复制进了「超算互联网」那一栏。
`sha256` 前 16 位一致（`a0d0a3386f967b06`）、长度都是 115、前缀都是 `sk-sp-`，就是判据。
**换 key 之后必须重新比哈希，不能凭「我改过了」结案。**

## 触发条件与影响

- 触发条件：一个客户端（这里是 CC Switch）里并存多个供应商，用户手动粘贴 key；粘贴时串栏。
- 影响：报错信息 `API 密钥无效` 会把注意力全部引向「端点/鉴权头/模型名」，实际上这三样全对。
  这也解释了同一个 key 在另一个供应商上**工作得好好的**——因为它本来就是那个供应商的 key。

## 三步判据（把「key 错」与「请求形态错」分开）

以本机超算互联网为例（`https://api.scnet.cn/api/llm/anthropic`，Anthropic Messages 协议，鉴权头 `x-api-key`）：

| 实验 | 期望 | 本机实测 |
|---|---|---|
| ① 该 key 打**它本命**端点（阿里云百炼 + `qwen4-max-preview`） | 200 | **200**，正常返回 → key 本身是活的 |
| ② **编造**一个 key 打同一端点 | 401 | **401 `invalid_api_key`** → 证明服务端确实在校验 |
| ③ 该 key 打**目标**端点（scnet + `SCNet-Max`） | 200 | **401 `Authentication Failed`** |
| ④ 换 `Authorization: Bearer` 打目标端点 | — | 回 `x-api-key不能为空` → **头名没错，是 key 不被接受** |

①+② 一起做才能排除「端点只是不校验」；③+④ 一起做才能排除「鉴权头写错了」。

## 根因分析

- CC Switch 的「DeepSeek Harness」接入**不走它自己的转发代理**（`live-state.json` 的 `apps` 里没有 dsh 条目，
  `cc-switch.log` 里也只有 `[Claude] >>>` / `[Codex] >>>`），它是**直接改写 DSH 的配置文件**：
  `D:\DevCache\.dsh\profiles\desktop\cordis.patch.yml` 的 providers 段 + `D:\DevCache\.dsh\.credentials.yaml` 的 `refs` 段。
  （`C:\Users\Admin\.dsh` 是指向 `D:\DevCache\.dsh` 的链接，读配置要认这个。）
- 两条 ref 分别由两个供应商的 `apiKeyEnv` 引用：`CC_SWITCH_DSH_TOKENPLAN`、`CC_SWITCH_DSH_SCNET_MAX`。
  用户在 UI 里只看到「一行一行的供应商」，看不到两个环境变量其实是同一个字符串。
- 于是 DSH 拿着百炼的 key 去打 scnet → 401 → 界面显示「API 密钥无效」。**报错文案没错，方向指错了。**

## 最小修复

在 CC Switch 里只改这一个供应商的 key（不要手工编辑 `.credentials.yaml`，会被 CC Switch 下次保存覆盖）：

```
CC Switch → DeepSeek Harness → 超算互联网 → 编辑 → 粘贴真 key → 保存
```

保存后 CC Switch 会重写两份文件。本机实测：`.credentials.yaml` 868B → **698B**，mtime 变成操作时刻。

## 验证记录（改完之后）

- 哈希对比：新 scnet key `len=43`、前 6 位 `sk-OTM`、`sha=ea18a55183522ba0`；
  tokenplan 仍 `len=115`、`sk-sp-`、`sha=a0d0a3386f967b06` → **已不同**。
- 直连 `POST /api/llm/anthropic/v1/messages`（`x-api-key` + `anthropic-version: 2023-06-01`，`SCNet-Max`）：
  - 非流式 → **200**，`usage{input 31, output 16}`、返回 `thinking` 块；
  - 流式 `stream:true` → **200**，正常 `message_start` + `content_block_delta`。
- 未验证：DSH 进程内是否立刻生效（宿主可能缓存凭据，重启一次即可，本人未实测）。

## 可复用规则

- **「密钥无效」先看是不是同一把 key 被填到了两处**：比 `sha256` 前 16 位，比长度，比前缀，三样一起看。
- 判定「服务端到底校不校验」，必须**用编造的 key 打一次**拿到 401；只看真 key 失败，分不清是校验还是别的问题。
- 判定「鉴权头对不对」，换一种头名再打一次，错误文案会直接告诉你缺哪个头（`x-api-key不能为空`）。
- 判「通没通」只认**真实补全请求**（200 + 有 content）；`/v1/models` 之类的轻量端点 200 不算数。
- 凭据文件由 GUI 工具托管时，**只通过 GUI 改**；手改会被下一次保存覆盖。

## 适用范围与不适用范围

- 适用：CC Switch / 各类多供应商面板里「同一个客户端并存多个 API 供应商」的场景。
- 不适用：单一供应商的 401（那是 key 真失效或额度问题）；走转发代理的模式（此时问题在代理侧日志，不在 credentials 文件）。

## 剩余风险

- 同库里 `codingplan`（摸鱼 CodingPlan）的 `options.apiKey` 是**空字符串**，同样不可用；切过去会得到另一条错误。
- CC Switch 每次 attach/detach 都会重写客户端 BASE_URL，若同时还接了 headroom 之类的中间层，要看接线守护是否把顺序搞反（见关联记录）。

## 关联

- [[03-通用/03-调试与验证/踩坑-API密钥报无效实为请求形态不对-OpenAI兼容网关|API 密钥报「无效」先看状态码：401 才是密钥问题，400 是请求形态问题]]
- [[03-通用/03-调试与验证/规则-CCSwitch接OpenAI兼容网关要四件套配置|CC Switch 接 OpenAI 兼容网关：apiFormat / isFullUrl / in_failover_queue / supportsThinking 四件套]]
- [[03-通用/03-调试与验证/规则-headroom省token串在ccswitch前面并加接线守护|headroom 省 token 必须串在 cc-switch 前面，并加接线守护]]
