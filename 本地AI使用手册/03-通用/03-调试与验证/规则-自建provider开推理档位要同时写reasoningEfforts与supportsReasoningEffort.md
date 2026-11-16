---
title: "给自建 provider 开推理档位：reasoningEfforts 的键与 supportsReasoningEffort 缺一不可"
date: 2026-11-01
domain: common
category: "调试与验证"
status: verified
severity: medium
stack: ["DeepSeek Harness", "pi-ai", "Cordis", "YAML", "OpenAI 兼容网关"]
tags: ["推理等级", "reasoningEffort", "reasoningEfforts", "thinkingLevelMap", "YAML 1.1", "DPI 感知", "截图取证"]
---

# 问题：官方模型卡片能选推理等级，自建 provider 的模型没有这一行

## 一句话结论

`reasoningEfforts` 决定「档位出现在选择器里」，`compat.supportsReasoningEffort: true`
决定「档位真的发给网关」——**两个都写才有效**。只写前者，下拉能选但请求里没有
`reasoning_effort`，选了等于没选。

## 触发条件与影响

- 项目或功能：DeepSeek Harness（0.2.1-rc.5）用 `@deepseek-ai/dsh-llm-pi-ai` 接自建 provider
- 环境与版本：Windows，网关为 OpenAI 兼容实现（本例 `https://www.workbuddy.ai/v2`）
- 触发条件：provider 用 `api: openai-completions` + 手写 `models` 清单
- 影响范围：模型能对话，但「推理等级」一栏为空，无法调思考强度

## 复现步骤

1. 前置条件：provider 下 `models` 只声明 `id/name/contextWindow/maxTokens`
2. 操作：打开模型选择器
3. 预期结果：有「推理等级」一行
4. 实际结果：只有模型名，没有档位

## 证据

配置生效前后，DSH 输入框的模型按钮文案：

```
改之前： Deepseek-V4.1-Flash
改之后： Deepseek-V4.1-Flash  Default      ← 档位那一格出现了
```

网关侧实测（同一把真密钥，`max_completion_tokens: 200`，统计 `reasoning_content` 字符数）：

| 模型 | 不发 | minimal | low | medium | high | xhigh | max |
|---|---|---|---|---|---|---|---|
| `deepseek-v4.1-flash` | 0 | 53 | 50 | 53 | 77 | 86 | 91 |
| `kimi-k3` | 21 | 43 | 12 | 80 | 121 | 55 | 127 |
| `glm-5.3` | 0 | 0 | 0 | 0 | 25 | 0 | 134 |
| `gpt-6-sol` | 0 | 0 | 0 | 0 | 0 | 364 | 366 |

七档全部 200，说明**发得出去、不报错**；但真正起作用的档位随模型而异。

## 根因分析

- 已确认的根因：
  1. 模型条目没声明 `reasoningEfforts` → `resolveModelReasoning` 返回 `reasoning: false` → 选择器不显示档位。
  2. `compat.supportsReasoningEffort` 缺省为假 → 派发链走到默认分支时不满足条件，`reasoning_effort` 不会被写入请求。
- 排除过的假设：网关不支持该字段（实测七档全 200）；需要设 `thinkingFormat`
  （不需要，pi-ai 的 `OPENAI_COMPLETIONS_REASONING_FIELDS` 已含 `reasoning_content`）。
- 问题归属：配置缺失，非代码 bug

## 修复方式

```yaml
        compat:
          supportsDeveloperRole: false     # 见关联记录：网关拒 developer 角色
          supportsReasoningEffort: true    # 关键：不写就不发 reasoning_effort
        models:
          - id: deepseek-v4.1-flash
            contextWindow: 300000
            maxTokens: 128000
            reasoningEfforts:
              'off':          # 必须加引号！
              minimal: minimal
              low: low
              medium: medium
              high: high
              xhigh: xhigh
              max: max
```

三个硬约束：

1. **键只能是** `off/minimal/low/medium/high/xhigh/max`。`resolveModelReasoning` 是按
   `THINKING_LEVELS` 逐项查表的，写别的键**不会报错、直接静默丢弃**。
2. **`off` 必须加引号**。YAML 1.1 把裸 `off:` 当布尔 `False`，键就废了（`'on'/'yes'/'no'` 同理）。
3. **`supportsReasoningEffort: true` 不能省**。派发链是
   `else if (options?.reasoningEffort && model.reasoning && compat.supportsReasoningEffort)`，
   少了它整段跳过。

配套：默认档位写在 `agent-default-model.reasoningEffort`，但**只对新建的 agent 生效**；
老会话的选择持久化在会话自己的 `modelSelection` 里，会显示 `Default`，手动选一次即可。

## 验证方式

- 网关侧：`probe_effort.py` 逐档发请求，统计 `reasoning_content` 字符数，确认档位确实改变了思考量。
- 客户端侧：`PrintWindow(hwnd, hdc, 2)` 渲染窗口截图，确认模型按钮出现档位文案。
- 反向验证：确认 `role: developer` 仍返回 400，说明 `supportsDeveloperRole: false` 未被推理开启后破坏。

## 复用要点

- **推理开启后 `supportsDeveloperRole: false` 更要检查**：`instructionRole` 的判定是
  `model.reasoning && compat.supportsDeveloperRole`，一旦 `reasoning` 变真，少了这条角色就会翻成 `developer`。
- **别用截图像素当"配置已生效"的证据**：先 `SetProcessDpiAwareness(2)`。
  不声明 DPI 感知时 `GetWindowRect` 返回虚拟化坐标、`ImageGrab.grab(bbox=)` 按物理像素裁，
  两套坐标系错位，截到的是**别的窗口的一块区域**——非常容易误判。
- **窗口被遮挡时用 `PrintWindow(..., 2)`**（PW_RENDERFULLCONTENT）直接渲染，不依赖前台。
- **两个 Electron 应用容易混**：按 PID 对应的 `ExecutablePath` 区分，别只看标题里的产品名。

## 关联记录

- `踩坑-API密钥报无效实为请求形态不对-OpenAI兼容网关.md`（同一网关的鉴权与请求形态问题）
