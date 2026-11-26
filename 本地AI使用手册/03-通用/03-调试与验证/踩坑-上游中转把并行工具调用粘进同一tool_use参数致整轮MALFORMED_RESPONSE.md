---
title: "上游中转把多个并行工具调用粘进同一个 tool_use 参数，导致整轮 MALFORMED_RESPONSE"
date: 2026-11-24
domain: common
category: 03-调试与验证
status: verified
severity: high
stack: ["DSH", "DeepSeekRuntime", "cordis", "llm-stream-repair", "TypeScript"]
tags: ["MALFORMED_RESPONSE", "工具调用", "流式响应", "llm/stream", "插件", "API中转"]
---

# 问题：DSH 会话反复「本轮运行失败」，报 Tool call 参数 JSON 末尾多出字符

## 一句话结论

中转层（`https://moyucccx.top`，provider `codingplan`）偶发把**同一 step 里的两个并行工具调用粘进同一个 tool_use 块的 arguments 分片流**（`{"a":1}{"b":2}`），DSH 解析该参数串报 `Unexpected non-whitespace character after JSON at position N`，把整个 chunk 流以 `finish{kind:'error', failure:{code:'MALFORMED_RESPONSE'}}` 终止 ⇒ 整轮对话报废、用户只能手打「继续」。写一个 `llm/stream` waterfall 插件，在检测到该错误时给未闭合的工具块补一个 `block-end`（携带**从拼接串里切出的第一个合法 JSON 对象**），并把终止原因改写成 `tool-calls`，即可让该轮继续跑完，且**只执行第一个调用**、由模型自己重发丢失的那个。

## 触发条件与影响

- 项目或功能：DSH（DeepSeekRuntime）所有会话，只要该 step 里有 ≥2 个并行工具调用
- 环境与版本：DSH 桌面版，profile `desktop`；默认模型 provider `codingplan` / `deepseek-v4.1-flash` / `reasoningEffort: xhigh`（`api: anthropic-messages`，baseURL `https://moyucccx.top`，中转链路 DSH → headroom:8787 → cc-switch:15721 → 上游）
- 触发条件：上游把两个工具调用的参数增量拼进同一个 `index` 的 `tool-call-delta`，第二个调用**连名字都没有**（流里没有第二个 `block-start`）
- 影响范围：命中率约 0.09%/步（全库 3265 个含工具调用的步中 3 例），但**每命中一次就整轮中止**；长任务（几十步）实际每天都撞几次，用户体感「老是中断」

## 复现步骤

1. 前置条件：会话里某一步需要并行发起两个工具（例如同时 `read` + `pwsh`）
2. 操作或命令：正常对话，无需特殊操作；用 `session.v4.jsonl.zstd` 复盘可直接确认
3. 预期结果：两个工具都执行
4. 实际结果：`本轮运行失败 Tool call "read": Unexpected non-whitespace character after JSON at position 51 (line 1 column 52)`，turn 结束

## 证据

三例同型（session-ba288472 turn1/turn2、session-82a4f1bb turn1），错误原文：

```
Tool call "read": Unexpected non-whitespace character after JSON at position 51 (line 1 column 52)

Received arguments:
{"file_path": "D:\\Skills\\skill-router\\SKILL.md"}{"description": "列出素材文件夹内容", "command": "Get-ChildItem ...
```

```
Tool call "send_meme": Unexpected non-whitespace character after JSON at position 28
Tool call "skill":     Unexpected non-whitespace character after JSON at position 24
```

流结构（assistant/attempt 记录）：

- 只有 **1 个** `block-start{index:0, blockType:'tool-call'}`
- 1 组 `tool-call-chunks{index:0, id:'call_00_...', name:'read'}`，其 arguments 分片拼接后是两个完整 JSON 对象**直接相连**
- 随后直接 `usage` + `finish{reason:{kind:'error', failure:{code:'MALFORMED_RESPONSE'}}}`，**没有 block-end**

会话日志位置与解压：`D:\DevCache\.dsh\sessions\<workspace>\<session>\session.v4.jsonl.zstd` 是多帧 zstd（本例 341 帧），`zlib.zstdDecompressSync` 只解第一帧，必须按魔数 `28 B5 2F FD` 切帧后逐帧解。

反证：全库 909/3265 步是 ≥2 并行工具调用且绝大多数成功 ⇒ **并行调用本身无罪**，问题是上游偶发合并。

第二类中断（另行记录、已由重试兜底）：`502 {"error":"cannot resolve tunnel destination moyucccx.top (ETIMEDOUT) ..."}`，走 `llm/retry`，策略 `["normal",5,["EMPTY_RESPONSE","RATE_LIMIT","SERVER","TIMEOUT","TRANSPORT"],500,10000,0.1]`。

## 根因分析

- 已确认的根因：**上游（中转）把同一 step 的多个并行工具调用合并进一个 tool_use 块**，第二个调用的 `name` 完全丢失，DSH 无从知道第二个工具是什么，只能在「解析参数 JSON」这一步抛 `MALFORMED_RESPONSE` 并终止整轮
- 排除过的假设：
  - 「并行工具调用太多」→ 909 步并行多数正常，代价大于收益，否决
  - 「DSH 的解析器写错」→ `JSON.parse` 对 `{}{}` 报错完全正确，DSH 无 bug
  - 「内核 asar 源码里能改」→ `D:\DeepSeekRuntime` 对会话进程整目录不可见（`Test-Path`/`icacls`/node `fs` 全失败，非 ACL 问题），且改 asar 会被下次自更新覆盖
- 问题归属：外部依赖（上游中转）

## 最小修复

写一个 profile 级宿主插件，**不改 app.asar**：`G:\AIrenwu\02_项目代码\dsh-llm-stream-repair\`

- 支点机制（读 `D:\DevCache\.dsh\profiles\desktop\node_modules\@deepseek-ai\dsh-llm\src\assembler.ts:77-84` 与 `:108-121` 确认）：`BlockAssembler` 收到 `block-end` 时 `partial.block = chunk.block`，`assemble()` 首行 `if (partial.block) return partial.block` ⇒ **block-end 携带的 block 是权威值，会覆盖累积的 delta 字符串**。所以补一个 `block-end` 就能把坏 arguments 换成合法 JSON。
- 接管点：`ctx.on('llm/stream', (options, next) => ...)`（该事件 mode=`waterfall`，签名 `(options, next): AsyncIterable<StreamChunk>`，`next()` 就是下游 adapter 流）。`dsh-llm/src/index.ts:1112-1138` 的 `adapterStream` 把 adapter 迭代异常就地转成终止 chunk、不向上抛，所以监听者一定看得到 `finish`。
- 修复逻辑：透传所有非 `finish` chunk 并累积每个 index 的 tool-call（id/name/args）；扣住终局 `finish`；若 `failure.code === 'MALFORMED_RESPONSE'` 或消息匹配 `/after JSON at position|Unexpected non-whitespace character/i`，则对未闭合的 tool-call 补 `block-end{index, block:{type:'tool-call', id, name, arguments: 第一个完整 JSON 对象}}`，可选插一条 text 提示，再发 `finish{reason:{kind:'tool-calls'}}`；切不出对象时按 `unsalvageableArguments: 'empty-object'` 兜底 `{}`；无关错误（502/SERVER 等）原样透传不改写。
- 配置：`enabled / notify / unsalvageableArguments / logCalls / logRepairs / logFile`，默认 `<DSH_HOME>/llm-stream-repair.log`；另内置一次性金丝雀（放置 `<日志目录>\llm-stream-repair.canary` 即令下一次模型调用返回合成假流，用完自动删文件）。

## 验证记录

- [x] 单元：`tools/selftest.mjs` 6 项全 PASS（切片器 / 正常流原样透传 / 粘连→只执行第一个+提示+本轮继续 / 抛异常形态也能修 / 无法切片兜底 `{}` / 无关错误不改写）
- [x] 端到端（真实主循环 + 金丝雀假流）：assistant 出现提示文本 → **真的派发了一次 `pwsh`** → 报 `invalid arguments: missing required property "description"`（证明 `command` 参数被保留且 JSON 可解析）→ 第二个 `CANARY-SHOULD-NOT-RUN` 未执行 → 本轮未中断；日志 `REPAIRED call=codingplan/deepseek-v4.1-flash blocks=[pwsh(args=77)] salvaged=1 unsalvageable=0`
- [x] 激活：`plugin_manager set_bundle` 返回 `{"changed":false,"application":"applied"}`，日志多一条 `APPLIED enabled=true notify=true unsalvageable=empty-object`
- [ ] 真实上游故障的后续命中（靠日志 `REPAIRED ...` 行长期观察）

## 可复用规则

1. **DSH 里「工具参数 JSON 非法」不该等于整轮报废**。给 provider 配中转时，先装 `llm-stream-repair` 再谈稳定性；判它有没有干活只看 `<DSH_HOME>\llm-stream-repair.log` 里的 `REPAIRED` 行。
2. **waterfall 型事件可以整条替换下游结果**：`ctx.on('llm/stream', (options, next) => 自己的 AsyncIterable)`。要改模型流行为，优先在这里做，不要去动 `app.asar`。
3. **`block-end` 的 block 是权威值**，能覆盖之前累积的 delta —— 这是修补坏参数最省事的手段。
4. 写 DSH 宿主插件：`export const inject = ['llm']` + `export function apply(ctx, pluginConfig)`。**配置是 `apply` 的第二个参数**；用 `ctx.config` 会报 `cannot get property "config" without inject`（插件装上了但 `did not activate`）。
5. 装本地 bundle 的正确顺序：`plugin_manager remove_bundle` → `install_bundle`（target 形如 `@local/dsh-llm-stream-repair@link:G:/...`）。**只在 profile `cordis.patch.yml` 手写 insert 行不会热生效**（启动时才组合，HMR 不监听）；直接 `install_bundle` 撞已有依赖会返回 `already-installed`。改完代码用 `set_bundle` 重载即可，不必重启宿主。
6. 日志是 UTF-8：`Get-Content` 必须加 `-Encoding UTF8`，否则中文显示成 `鐢ㄥ亣娴佹浛鎹?` 这种乱码，别误判成写入坏了。

## 适用范围与不适用范围

- 适用：DSH 走中转/聚合网关（anthropic-messages 或 openai-completions 皆可）时出现「参数 JSON 末尾多字符 / 两个对象粘连」类失败
- 不适用：单一工具调用被截断（`max-tokens` 截流）、工具名本身缺失、上游 5xx 隧道故障（那是重试层的事，插件故意不改写）

## 剩余风险

- 修复只能**保住第一个调用**，第二个调用的名字在上游已经丢失，无法恢复，必须由模型下一 step 重发（提示文案已引导）
- 若上游把两个调用的**参数交错**（而非顺序粘连），切片器可能切不出合法对象，落到 `{}` 兜底，工具会报参数缺失（可接受，仍不毁轮）
- 插件依赖 `llm/stream` 事件契约，大版本升级后需复核（`dsh-llm` 的 `GenerateOptions`/`StreamChunk` 若改名要同步）

## 关联

- 相关记录：[[踩坑-会话进行中装插件致热重载报service-unavailable]]、[[踩坑-DSH插件package.json带BOM致整包被内核静默跳过]]、[[经验-DSH装插件与删provider的四个动作点]]、[[踩坑-bundle旧版依赖盖住内核同名包致启动失败]]、[[规则-Electron的app.asar可直接按头解析取文件无需asarCLI]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码：`G:\AIrenwu\02_项目代码\dsh-llm-stream-repair\index.js`、`...\cordis.patch.yml`、`...\tools\selftest.mjs`
- 相关配置：`D:\DevCache\.dsh\profiles\desktop\package.json`（`dsh.profile.bundles` 末项）、`D:\DevCache\.dsh\profiles\desktop\cordis.patch.yml`（provider `codingplan`）、`D:\DevCache\.dsh\llm-stream-repair.log`
