---
title: "逆向工具箱 06-skill-mcp-3.0 清单、后端选型决策表与本机实测"
date: 2026-10-11
domain: common
category: 03-通用/02-AI协作与提示词
status: verified
severity: low
stack: [MCP, js-reverse-mcp, Camoufox, CloakBrowser, WMPFDebugger, Qoder]
tags: [工具箱清单, 选型, MCP]
---

# 规则：这套逆向后端该怎么选（含本机可启动性实测）

来源：`H:\下载\06-skill-mcp-3.0`（6 个 zip，共约 1.19 GB）。本文件只记**已核实的身份与实测结果**，
未跑通的部分一律标"未验证"。

## 一、包里到底有什么（身份取自各自 README / package.json 原文）

| 文件 | 是什么 | 内部 MCP / skill 名 | 版本 |
|---|---|---|---|
| `trace（skill）.zip` | 纯 Web 协议逆向总控 skill（211 文件，含 10 套验证码 playbook） | skill 名 **`spider-king`**（与目录名不同） | — |
| `wechat-miniapp-reverse(...).zip` | 微信小程序 / WMPF 调试 skill，承担 WMPF 内 `Observe`/`Capture` | `wechat-miniapp-reverse` | — |
| `CloakBrowser.zip`(315MB) | 定制 Chromium 146 + JS 逆向 MCP | `js-reverse-mcp` | **3.0.9** |
| `Camoufox.zip`(630MB) | 反指纹 Firefox + 逆向 MCP | `camoufox-reverse-mcp` | — |
| `FireFox Reverse AI.zip`(151MB) | Firefox 逆向浏览器 + "强模型领航/便宜 worker 实操"成本分流 | `frx-director-mcp` | 0.2.0（内置 44 工具） |
| `WMPFDebugger.zip`(87MB) | 第三方开源（evi0s, GPL-2.0）frida 强开小程序完整 CDP | 内含 `miniapp-reverse-mcp` | 1.0.0 |

`trace` 唯一内置实战案例 = **抖音 Web `a_bogus` 纯 Python 维护线索**。它自己声明边界：
不含 `id146/147/148` 位级公式、`fields[24..87]` 完整构造、最终 payload 布局与动态 alphabet 推导，
**只有该文件 + bundled primitives 时不得声称已恢复完整生成器**。

## 二、选型决策表（提炼自 `trace/references/mcp-routing-playbook.md` 的 Triage table）

| 你手上的情况 | 走法 | 用哪个后端 | 被动/环境侧 |
|---|---|---|---|
| 已有 HAR / 请求文本 / cookie-token 样本 / JS·WASM 文件 / 固定向量 | `artifact-only`，**不开浏览器** | 无（静态 AST / 纯 Python 重建） | 样本文件 |
| 只有一条 URL、站点未知、指纹压力低或未知 | `live-target` + 侦察 | **默认 `chrome-devtools`**；若已经要下 DP/取 initiator，就让 `js-reverse` 一机双职，**不要再开第二个 Chrome** | 可事后接 Reqable |
| URL + 指纹压力高（明确反指纹、干净浏览器被拒、同一路径反复失败、用户要求隐身） | `live-target`，先起宿主 | **Camoufox / 受管 profile 先做干净基线**，再按情况接 `js-reverse` | Camoufox / AdsPower |
| 请求已知但字段在变、签名失败 | 基线交接后进 `debugger-trace` | `js-reverse` | Reqable 定"真实出口" |
| attach 拿不到 / `select_page` 超时 | 记 `debugger_attach_gap` | 走 HTTP 收脚本；有后端则 `silent-value-capture` | — |
| Hook 会污染观测、JSVM 公共边界值取不到 | 立刻开 `silent-value-capture`；没有就记 `silent_value_capture_gap` | — | — |
| 浏览器能过、脚本在业务语义前就失败 | `transport` | 通常不开浏览器 | WireMCP / PCAP |
| 交付采集器 | `python-collector` | **无浏览器、无 MCP 运行时** | 只用历史证据 |

硬规矩：同一时刻只允许**一个** `TARGET_ACTIVE` 浏览器族，串行交接；`Camoufox` 只是基线宿主/环境面，
**不能替代 `js-reverse`，也不能当采集器运行时**；最终交付路径必须 browser-free。

## 三、本机实测（2026-10-11，全部有输出留档）

- 运行时：node **v24.15.0**、python 3.14.2。`js-reverse-mcp` 的 engines 是 `^20.19 || ^22.12 || >=23` → **满足**。
- 包内**自带 `node_modules`**（解出 23597 文件 / 194 MiB，其中 99% 是 node_modules）→ **不需要 npm install**。
- stdio 握手实测：`initialize` 与 `tools/list` 均 **0.7–0.9s** 应答（连测两次一致），
  serverInfo=`js-reverse 3.0.9`，**90 个工具**：reverse_engineering 37 / debugging 22 / network 13 / navigation 12 / browser_state 6。
  含 `break_on_xhr`、`get_request_initiator`、`hook_jsvmp_interpreter`、`verify_signer_offline`、`trace_property_access`、`capture_heap_snapshot` 等。
- **未复现的一次异常**：第一次探针只给 7.5s 窗口时收到 0 条响应，之后同样脚本给 25s 窗口就正常。
  怀疑是冷启动（首次读大量文件）超过 7.5s，但**没有复测冷启动路径，此结论未证实**。
- 浏览器**没有真起**（`getContext()` 是首次调用工具时才 launch，握手阶段不碰浏览器）→ 真跑站点前的行为未验证。
- 默认用系统 Chrome；`--cloak` 才用 CloakBrowser 二进制，且**不带 `--cloakBinaryPath` 时首次会静默下载 ~200MB**，
  看起来像卡住（README 自己这么警告）。

## 四、Qoder 侧识别规则（探针实测，2026-10-11）

- 技能扫描根：`C:\Users\Admin\.qoder\skills\`，现有 7 项全是 **Junction → `D:\QoderToolkit\<名>`**。
- **登记用的是目录名，不是 frontmatter 的 `name`**：探针目录 `probe-shape-test` + `name: spider-king-probe`
  → 列表里出现的是 `probe-shape-test`。
  ⇒ 装 `trace` 会以 **`trace`** 出现（不是 `spider-king`）；想让名字一致就得把目录改成 `spider-king`。
- `argument-hint`、`compatibility` 等 Claude Code 风格的多余 frontmatter 字段**不影响识别**。
- 探针已删除，技能列表恢复原状。

## 五、未验证 / 剩余风险

- `camoufox-reverse-mcp`、`miniapp-reverse-mcp`、`frx-director-mcp` **都没做握手实测**。
- 没测真起浏览器后的反检测效果，也没测任何目标站点。
- 装进 `~/.qoder/skills` 后这些逆向 skill 会不会被自动触发（其 description 里有大量强触发关键词），未评估。
- 合规：反检测 + 协议逆向工具，真实目标需自行把握授权范围。

## 关联

- 相关记录：[[规则-Windows新窗口默认居中只能常驻监视器]]（同属"工具能力要实测登记，别凭名字推断"）
- 相关分类：[[03-通用/02-AI协作与提示词/README|AI 协作与提示词]]
- 取证脚本与原始输出：`G:\AIrenwu\01_任务归档\2026-10-11_逆向工具箱体检\03_工具脚本\mcp_probe2.py`、
  `mcp_latency.py`、`02_证据日志\mcp-handshake.txt`
