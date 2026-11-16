---
title: "headroom「省了 99.8%」是上游 prompt 缓存伪造的；离线闸还会静默关掉 ML 压缩器"
date: 2026-11-15
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: high
stack: [headroom-ai, onnxruntime, huggingface, tiktoken]
tags: [省token, 测量陷阱, prompt缓存, 离线, hf-mirror, Kompress]
---

# 踩坑：单发探针测出的省量是假的，且 HEADROOM_OFFLINE=1 会让 ML 压缩器一直没启用

## 一句话结论

两件事都会让人误判 headroom 的效果：
① **单发对比探针测出的「省 99.8%」其实是上游 prompt 缓存**，不是 headroom 压缩；
② `HEADROOM_OFFLINE=1` 挡住模型下载，**ML 压缩器（Kompress）从头到尾没加载**，
而它的报错写的是 `requires onnxruntime or torch`，把人引向完全错误的方向。

## 触发条件与影响

- 环境：headroom-ai 0.44.0（`[proxy]`），venv 在 `D:\uv\tools\headroom-ai\`（**目录名是 headroom-ai 不是 headroom**），
  CLI `D:\uv\bin\headroom.exe`。
- 触发：用「同一份大 payload 分别打直连和经 headroom，比 `input_tokens`」来验收省量。
- 影响：会得出「省 99.8%」的假结论并对外汇报；同时真实省量远低于应有水平（ML 压缩器没开）。

## 证据

**假省量**：direct `input_tokens=64139` vs headroom `139`，看着省 99.8%。
但 headroom 自己的账本写着 **`tok_saved=0 cache_read=64000`** —— 第一跳把上游 prompt 缓存写热，
第二跳白捡。**用唯一 seed 打散缓存重测，真实差值只有 0.4%（34272 vs 34144）。**

**Kompress 没加载**（`~\.headroom\logs\proxy-8787.log`）：

```
Kompress: 'onnx/kompress-int8-wo.onnx' for chopratejas/kompress-v2-base is not cached
and HEADROOM_OFFLINE forbids fetching it
Kompress: background model download failed ... Kompress requires onnxruntime or torch
```

**那句 requires onnxruntime or torch 是误导**：实测 venv 里 onnxruntime 1.32.0 / tiktoken 0.14.0 /
transformers 5.23.0 / huggingface_hub 1.33.0 全部在位（torch 缺失但不需要）。真因是离线闸。

## 根因分析

- 已确认根因 1：上游 provider 的 prompt 缓存会跨请求命中，单发对比探针无法区分「压缩省的」与「缓存省的」。
- 已确认根因 2：`HEADROOM_OFFLINE=1` 禁止一切外网，模型不在本地缓存就永远加载不上；
  错误信息把「缺模型」写成了「缺运行时」。
- 排除过的假设：onnxruntime 缺失（实测在位）；headroom 版本 bug（预置模型后立刻正常）。
- 问题归属：环境或依赖 + 测量方法错误。

## 最小修复

### 1. 预置模型缓存，**保持 HEADROOM_OFFLINE=1 不动**

依据 `headroom/onnx_runtime.py:146` 的 `hf_hub_download_local_first()`：
**先 `local_files_only=True`**，离线闸只拦网络回退。docstring 明说
「a pre-seeded air-gapped deployment keeps working, which is the whole point of pre-seeding」。

- `huggingface.co` 本机超时 10060（21s）；**`hf-mirror.com` 200/991ms** → 用镜像下载。
- 按 headroom 自己钉的 SHA（`onnx_runtime.py:73-90 _PINNED_REVISIONS`）预置到 `HF_HOME=D:\uv\data\huggingface`：
  - `chopratejas/kompress-v2-base` @ `b1563631b35bfdcee37587ad530147497d820d4c`
    → `onnx/kompress-int8-wo.onnx` **261.4 MB**
  - `answerdotai/ModernBERT-base` @ `8949b909ec900327062f0ebf497f51aef5e6f0c8` → 分词器 vocab=50368
- 脚本：`D:\Skills\skill-router\seed_kompress.py`（设 `HF_ENDPOINT=https://hf-mirror.com`、
  `HF_HUB_OFFLINE=0` 下载，之后 cache-only 复查双双 HIT）。
- ONNX 候选顺序：`kompress-int8-wo`(261MB) → `fp32`(601MB) → `int8`；可用
  `HEADROOM_KOMPRESS_ONNX_FILENAME` 钉死。

**验证成功**：`Kompress ONNX loaded: chopratejas/kompress-v2-base backend=onnx total_ms=1182`、
`warmed in the background in 1187 ms`，之后持续
`Kompress slow compress backend=onnx words=762 chunks=6 inference_ms=2620 ratio=0.962 saved=92`。
高负载时 `execution saturated ... skipping chunk` / `hit 20.0s deadline ... kept remainder verbatim`
是**优雅降级，正常**。

### 2. 补上 headroom 自带的 `coding` profile（原本漏了）

依据 `headroom/agent_savings.py:149-185`：cache 模式只压最新增量，增量就是 tool/user 观测，
**`COMPRESS_USER_MESSAGES` 不开就没东西可压**。
用 `headroom agent-savings --profile coding --format shell` 渲染的 19 个变量部署，关键项：
`COMPRESS_USER_MESSAGES=1`、`PROTECT_RECENT=0`、**`PROTECT_READS=1`**、`ACCURACY_GUARD=strict`、
`CODE_AWARE_ENABLED=1`、`DEDUPE=1`、`TOOL_SEARCH=1`、`MIN_TOKENS=10`、`LOSSLESS_THEN_LOSSY=1`。

### 3. 顺手修掉的两个告警

- `tiktoken encoding 'o200k_base' did not load within 10.0s (likely a stalled vocab download)`
  → 加 `--env HEADROOM_TIKTOKEN_LOAD_TIMEOUT_SECONDS=2`。
- `Unknown Anthropic model 'deepseek-v4.1-flash': ... conservative default (128,000 tokens)`
  → 建 `~\.headroom\models.json`（schema 见关联规则条）。

## 验证记录

- [x] 模型 cache-only 复查：两个仓库双双 HIT
- [x] 日志出现 `Kompress ONNX loaded` + 持续 `Kompress slow compress ... saved=92`
- [x] `headroom savings` 账本：修前 262,146/2,718,965（$0.5268，23 calls）
      → 修后 **394,188/6,469,913（6.1%，新增输入 13.7%），$0.8044，65 calls**
- [x] `ops.py savings` 子命令会检查日志里有没有 `Kompress ONNX loaded`，没有就警告并指向 seed 脚本

## 可复用规则

1. **判 headroom 有没有在省，只认 `headroom savings` 持久账本 + 真实多轮流量。**
   单发对比探针的 `input_tokens` 差值不可信。
2. 合成探针「测出 0」有三个**正常**原因，别当故障（都已从源码/日志核实）：
   - 单发冷请求没有上一轮前缀 → 整段历史算 frozen prefix（`route_counts={'user_msg':1} compressed=0 frozen=7`；
     依据 `content_router.py:6410-6414 prefix_replay_guaranteed`）
   - 工具名是 `read_file` → `PROTECT_READS=1` 主动排除（`excluded_tool`），保字节精确供 Agent 打补丁
   - 十几万 token 的密集 JSON → `ratio_too_high`，strict 精度闸拒绝压缩
3. **报省量时不要说「省了百分之几」**（上游 SKILL.md 明令），只打印 before/after 与账本数字。
4. **`D:\uv\data\huggingface\hub\` 那 261MB 别清**——清了 Kompress 静默退回结构压缩，
   不报错，只是省得少。
5. 见到「缺运行时」类报错先实测依赖是否在位，再怀疑是不是**离线闸把「缺模型」写成了「缺运行时」**。

## 适用范围与不适用范围

- 适用：本机 headroom-ai 0.44.0 代理模式、`HEADROOM_OFFLINE=1` 的部署。
- 不适用：允许外网的部署（模型会自动下载，但仍要按钉住的 SHA 核对）。

## 剩余风险

- 上游 prompt 缓存命中率随流量变化，账本里的百分比会波动，不是固定值。
- Kompress 在 CPU 上有 20s _deadline_，超大 payload 会部分保留原文，属预期行为。

## 关联

- [[规则-headroom省token串在ccswitch前面并加接线守护]]
- [[踩坑-路由熔断红标是历史失败且探针自身会造假故障]]
- [[踩坑-GitHub大包推送被重置需分块推送]]（同类「本机网络对特定域名不通，换镜像/出口」）
