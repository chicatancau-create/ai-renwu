---
title: "API 密钥报「无效」时先看状态码：401 才是密钥问题，400 是请求形态问题"
date: 2026-11-01
domain: common
category: "调试与验证"
status: verified
severity: medium
stack: ["OpenAI 兼容网关", "DeepSeek Harness", "WorkBuddy", "Python"]
tags: ["API密钥", "401", "400", "SSE流式", "system角色", "凭据复用", "排障方法"]
---

# 问题：密钥填对了却一直报「API 密钥无效」，反复改配置无效

## 一句话结论

**401 与 400 是两回事**：`401 + {"message":"not_found"}` 才是密钥不被认；
一旦返回 **400**（哪怕是 `Non-stream ... not supported`、`first message is not system prompt`），
说明**鉴权早已通过**，问题在请求形态。继续改密钥或改地址都是白费。

## 触发条件与影响

- 项目或功能：把 WorkBuddy 的 `ck-` 访问密钥接入 DeepSeek Harness（DSH 0.2.1-rc.5）
- 环境与版本：Windows 10/11，DSH 0.2.1-rc.5，网关 `https://www.workbuddy.ai/v2`
- 触发条件：用 OpenAI 兼容协议接一个「非标准」网关
- 影响范围：客户端报「API 密钥无效」「获取模型失败」，用户会误以为密钥复制错了

## 复现步骤

1. 前置条件：密钥已保存在客户端凭据里
2. 操作：用该密钥 POST 网关 `/chat/completions`
3. 预期结果：200 或 401
4. 实际结果：**400**，报错内容与密钥毫无关系

## 证据

同一把真密钥，同一端点，只改请求形态：

| 请求形态 | 返回 |
|---|---|
| 非流式 `stream:false` | `400 {"code":11101,"msg":"Non-stream chat request is currently not supported"}` |
| 流式，首条是 `user` | `400 {"code":11128,"msg":"first message is not system prompt"}` |
| 流式，首条角色写 `developer` | `400 {"code":11128,"msg":"Illegal API invocation from an unapproved channel"}` |
| 流式，首条是 `system` | **200**，正常吐字 |
| 同一密钥打到国内站 `copilot.tencent.com/v2` | `401 {"message":"not_found"}` |

反向证据：故意用假密钥（格式合法）打国际站，返回的也是 `401 not_found`。
**所以 401 只代表"这把密钥这个网关不认"，不代表请求写错了。**

## 根因分析

- 已确认的根因：该网关是定制实现，硬性要求 ① 必须 `stream:true` ② 首条消息必须是 `system` 角色。
- 排除过的假设：密钥复制不全（格式探测已通过，`invalid_format` 与 `not_found` 能区分开）、
  网络/代理（同机其他请求正常）、模型名不存在（换成不存在的模型会返回另一种错误 `11102`）。
- 问题归属：环境或依赖（网关特殊约束），非代码 bug

## 修复方式

1. 协议用 `openai-completions`，`baseURL` 用 `https://www.workbuddy.ai/v2`（**不要** `/v1/messages`，国际站该路径 404）。
2. 若客户端框架（如 pi-ai）可能把系统提示词写成 `developer` 角色，显式关掉：
   ```yaml
   compat:
     supportsDeveloperRole: false
   ```
   其判定源码为 `model.reasoning && compat.supportsDeveloperRole ? "developer" : "system"`，
   因此**不要**给该模型声明 `reasoning`，可作第二道保险。
3. 模型 ID 不要猜，从账号目录缓存取（见下）。

## 验证方式

- 用真密钥跑 6 种请求形状：最小流式 / `tools+tool_choice` / `stream_options` /
  `temperature+top_p` / `reasoning_effort` / `max_tokens=128000` —— 全部 200。
- 工具调用确认：`tool_call_deltas=8`，说明 function calling 可用。
- 配置写入后重启客户端，模型选择器正确显示新模型名，说明配置 schema 也接受了。

## 复用要点（换任何网关都适用）

1. **先分级判读状态码再动手**：401=身份，400=参数/形态，403=权限，404=路径，429=额度。
2. **密钥不进模型上下文也能验证**：多数客户端把密钥明文存在本地凭据文件里，
   写脚本读取后直接发请求，只打印状态码 + 密钥指纹（长度/前3位/末2位），密钥永不出现在对话里。
   DSH 的 `.credentials.yaml` 中 `refs:` 存的就是密钥本体（按环境变量名索引），不是句柄。
3. **模型 ID 从本地目录缓存取**：DSH 会在 `~/.dsh/.workbuddy-ai-catalog.json` 缓存账号可用模型
   （`source: workbuddy-ai:app`）。注意同目录下可能还有**另一个账号**的缓存
   （`source: workbuddy:cli`），不要混用。
4. **别把 `11102 model ... not found` 和 `11133 request parameters were rejected` 混为一谈**：
   后者往往是 `max_tokens` 给太小（推理模型），换成 `max_completion_tokens: 64` 就通了。
5. **`*/v1/models`、`*/v2/models` 全部 404** 时，「获取可用模型」按钮必然失败，
   这不是故障，只能显式列 models。

## 关联记录

- `规则-Electron的app.asar可直接按头解析取文件无需asarCLI.md`（用同样手法取到适配器 README 与源码）
