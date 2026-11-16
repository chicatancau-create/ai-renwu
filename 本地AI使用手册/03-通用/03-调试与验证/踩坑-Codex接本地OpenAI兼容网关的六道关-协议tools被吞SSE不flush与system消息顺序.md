---
title: "把 Codex CLI 接到本地 OpenAI 兼容网关：六个独立死点，逐个踩过并验证"
date: 2026-11-15
domain: common
category: "调试与验证"
status: verified
severity: high
stack: ["OpenAI Codex CLI v0.155.1", "llama.cpp b10837", "牧羊人 Herdsman v0.6.7", "Python 标准库代理", "Windows 11"]
tags: ["Codex", "Responses API", "wire_api", "SSE流式", "flush", "system消息顺序", "tools被吞", "config.toml", "本地大模型"]
---

# 问题：Codex 接本地模型，一路报五种不同错误，最后一种最难找

> 六个死点各自独立——修掉前面的才会暴露后面的，所以必须全部满足才通。
> 每条都有复现与验证，见对应小节和「验证记录」。

## 一句话结论

接本地 OpenAI 兼容网关给 Codex CLI 用，要同时过六道关：**协议选 responses、别用宿主网关（它吞 tools）、
代理转发 SSE 必须逐块 flush、本地 provider 千万别加 `requires_openai_auth`、`env_key` 指的变量必须真的存在、
模型模板要求 system 消息唯一且在首位**。全部满足后 `codex exec` 实测 `exit=0`。

## 触发条件与影响

- 项目或功能：把本地 llama.cpp 模型（牧羊人托管）接进 IDE 里的 Codex 编程插件
- 环境与版本：Codex CLI v0.155.1 / llama.cpp b10837（PrismML fork）/ 牧羊人 v0.6.7 / Win11
- 触发条件：按 OpenAI 官方惯例写 provider 配置
- 影响范围：五种报错互相掩护，会反复误判成「密钥错了」「网络断了」「配置没生效」。
  最终用户放弃该路线，改把模型当纯本地写作助手用——**所以本条主要是别重复踩**

## 六个死点（按暴露顺序）

### ① 新版 Codex 删了 `wire_api = "chat"`

```
Error loading config.toml: wire_api = "chat" is no longer supported.
How to fix: set wire_api = "responses"   （codex discussions/7782）
```
只能走 Responses API。⇒ 上游必须有 `/v1/responses`。

### ② 宿主网关有 `/v1/responses`，但会把 `tools` 吞掉

同一时刻、同一 payload 的对照（这是最关键的一组数据）：

```
网关 8080/v1/responses + tools=[get_weather] → output 只有 [message]，无调用
直连 1544 /v1/responses + tools=[get_weather] → [reasoning, function_call]
                                               arguments={"city":"广州"}
```

**⇒ 别用宿主的网关。** 另外它的 `POST /v1/completions` 返回 HTTP 200 但 body 是空的，
比 404 更阴——只看状态码的插件会以为成功。

### ③ 代理转发 SSE 不逐块 flush ⇒ 客户端报「流断了」

自己写的转发器把上游 SSE 读完再一次性吐，Python 侧「读完全文」数行数看不出来，
Codex 侧直接失败：

```
stream disconnected before completion: error sending request for url (http://127.0.0.1:8081/v1/responses)
```

修复＝每个 chunk 写完就 `flush()`（chunked 编码写完 `0\r\n\r\n` 也要 flush）。验证只看**首块到达时间**：

```
修前：首块 6.50s，末块 10.50s（跨 4.0s，最后一秒内到达 78 行）＝攒完再吐
修后：首块 0.29s，末块 3.26s                              ＝真增量
```

### ④ 本地 provider 加 `requires_openai_auth = true` 会把 key 送去 api.openai.com

```
warning: Falling back from WebSockets to HTTPS transport.
ERROR: unexpected status 401 Unauthorized: Incorrect API key provided: sk-ptw-1****EzXi.
       url: https://api.openai.com/v1/responses
```

这个标志是给 ChatGPT/OpenAI 官方认证用的，加上后 Codex 根本不看你的 `base_url`。
**⇒ 本地/自建 provider 一律不要加。**（同时：这把 key 是被送到外部域名才被拒的，
属于凭据外流，哪怕目标域名是官方的也不算无害。）

### ⑤ `env_key` 读的是环境变量，不看 auth.json

```
ERROR: Missing environment variable: `OPENAI_API_KEY`.
```
`env_key = "X"` 时 Codex 只要**环境变量** X。两个办法：给本地 provider 用专属变量名
（值随便，本地不校验）并 `setx` 到用户级——**注意设完必须重启宿主程序/IDE，子进程才看得到**；
或者不写 `env_key`。

⚠️ 顺带一个真实损失：CC GUI 那类客户端的「auth.json」输入框写的是**全局共享**的
`~/.codex/auth.json`（只有一行 `OPENAI_API_KEY`，所有 provider 共用）。
往里填占位值会**直接顶掉用户真 key**。本机靠应用自己的 `auth.json.cli_backup` 恢复
（判据：真 key 44 字符、前缀 `sk-ptw-`；占位值只有 5 字符）。
⇒ 本地 provider 用**独立变量名**，完全不碰 auth.json，就不会有这个问题。

### ⑥ 真正的 500：模型模板要求 system 消息唯一且在首位

llama.cpp 会把 Responses 请求里的 `instructions` 转成开头的 system 消息，
而 Codex 的 `input[0]` 又是一条 `role="developer"`（同样转成 system）⇒ 两条 system，
第二条不在首位 ⇒ 模板里的 `raise_exception` 抛异常：

```
HTTP 500  Jinja Exception: System message must be at the beginning
```

二分定位过程（回放抓到的真实请求逐段裁剪）：

```
原样                                → HTTP 500  System message must...
删掉 developer 项                    → OK
把 developer 合并进 instructions     → OK   ← 采用，内容不丢
```

⇒ 代理里做规范化：把 `input` 中所有 `developer`/`system` 项的文本折进 `instructions`
再从 `input` 删除。日志验证 `merged_system: 3, status: 200, empty_answer: false`。

### 附带一条：小 `max_output_tokens` 会让模型「答不出话」

带隐藏思考的模型，输出预算太小时**正文长度为 0**，客户端就报
`All connected models failed to generate a response`——和显存、网络都无关：

```
max_output_tokens=40  → items=[reasoning]          正文 0 字
max_output_tokens=120 → items=[reasoning]          正文 0 字
max_output_tokens=600 → items=[reasoning, message] 正文 439 字
```
⇒ 代理里把小于 4096 的预算抬到 4096（客户端不改也能通）。

## 取证方法（这次真正救命的三条，与上面六道关同样可复用）

1. **别猜客户端发了什么，把请求原样落盘再离线二分。** 在代理里 dump 每次 POST 的
   完整 body + 一行 `{规模/是否合并/上游状态/正文空不空}`，就能逐字段裁剪复现。
   ⚠️ 日志要写到项目目录，不要只放 `%TEMP%`——本机 TEMP 是易失层，一次系统更新重启就清空。
2. **TOML 顶层键必须写在第一个 `[table]` 之前。** 用脚本往 config 末尾**追加**
   `model = ...` / `model_provider = ...`，它们会落进上一个表里而完全失效——
   表现是「改了没反应」，本机因此白测了三轮。改完看客户端自报的抬头（Codex 打 `provider: <名字>`）。
3. **判「有没有走某条协议」用最小差异对照**，别用整体成功/失败判断。
   例：加一个 `tools` 字段，看输出里有没有 `function_call`；改一个 flush，看首块时间。

## 最终可用配置（六道关全过）

```toml
model = "bonsai-main"
model_provider = "localgw"
model_reasoning_effort = "low"

[model_providers.localgw]
name = "localgw"
base_url = "http://127.0.0.1:8081/v1"   # 自己起的转发器，不是宿主网关
env_key = "LOCAL_GW_KEY"                 # 独立变量名，别用 OPENAI_API_KEY
wire_api = "responses"
```

转发器需具备：自动发现上游随机端口、SSE 逐块 flush、developer/system 合并、小预算抬高。

## 验证记录

- [x] 协议：`/v1/responses` 在 llama-server 直连可用（text / reasoning / function_call / SSE 事件齐全）
- [x] 吞 tools：网关 vs 直连同 payload 对照，已复现并记录（见 ②）
- [x] flush：修前首块 6.50s vs 修后 0.29s，最后一秒到达行数 78→真增量
- [x] auth：`requires_openai_auth=true` 复现 401 外流；改独立 `env_key` 后复现缺失变量并修复
- [x] 500：三种裁剪结果如实记录，采用合并方案后 `status: 200`
- [x] 端到端：`codex exec` 返回 `exit=0`、正文正常、94 tokens
- [x] 回放：Codex 原样请求（13 tools / 57K 输入 / 流式）经代理 → 首块 ~30s、正文正常
- [ ] 未覆盖：长会话多轮工具调用的稳定性（只验到单轮 + 一次工具返回）
- [ ] 现状：**该路线已由用户决定放弃并全部回滚**，本条留作再次尝试时的清单

## 可复用规则

接任何「只支持 Responses API 的新客户端」到本地/自建 OpenAI 兼容后端时，
**先单独验三件事**：① 上游是否实现 `/v1/responses`；② 它是否保留 `tools`；
③ 目标模型的 chat template 对 system 消息位置/数量有什么硬约束。
三者任一不满足，都需要一层会改请求体的转发器，而不是去调客户端参数。

## 适用范围与不适用范围

- 适用：Codex CLI 及一切 Responses 协议客户端接 llama.cpp / Ollama / 各家本地网关；
  任何自己写 HTTP/SSE 转发器的场景
- 不适用：纯 Chat Completions 客户端（Continue、Cline 等）—— 那条路上没有 ①④⑥；
  官方 OpenAI 上游本身（④⑤ 反而是必须的）

## 剩余风险

- llama.cpp 的 Responses 实现仍在演进，②⑥ 的行为可能随版本变化；每次升级后需重跑 ①②③ 三查。
- 本地模型带思考时，抬高输出预算会把首字延迟拉长（本机 Codex 单请求首块约 30s），
  客户端超时设得短会误判成失败。

## 关联

- 相关记录：[[规则-CCSwitch接OpenAI兼容网关要四件套配置]]、
  [[踩坑-API密钥报无效实为请求形态不对-OpenAI兼容网关]]、
  [[踩坑-CCSwitch多供应商共用同一把密钥致换key无效]]、
  [[踩坑-笔记本功耗封顶让同一配置吞吐差十倍-tok每秒不能当基线]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关文档：`D:\Models\Ternary-Bonsai-2-27B-gguf\部署交接说明.txt` 第十一节（本项目全过程留档）
