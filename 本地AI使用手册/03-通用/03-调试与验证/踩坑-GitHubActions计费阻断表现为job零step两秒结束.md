---
title: "GitHub Actions 计费阻断：job 零 step、2 秒结束、日志 404，真因只在 check-run annotations 里"
date: 2026-11-15
domain: common
category: 03-调试与验证
status: verified
severity: high
stack: [GitHub Actions, gh CLI, REST API]
tags: [CI, 计费, 假失败, 取证判据, annotations]
---

# 问题：所有 workflow 都 failure，但代码没问题——是账户付款被拦，job 根本没启动

> 事发 2026-11-11，2026-11-15 回写。

## 一句话结论

Actions 的 `permissions.enabled=true` **不代表能跑**。账户付款失败/额度用尽时，
GitHub 仍会创建 run 和 job 并标 `failure`，但 **job 里 0 个 step、2 秒结束、没有 runner、日志 blob 404**。
唯一写明原因的字段是 **check-run 的 annotations**：
`The job was not started because recent account payments have failed or your spending limit needs to be increased.`
拿不到这句就会误判成「代码坏了」，白查几小时。

## 触发条件与影响

- 项目或功能：判断「CI 全绿」能不能写进交付结论
- 环境与版本：GitHub 免费账户 + 私有仓库；`gh` CLI 已认证
- 触发条件：账户有未付款账单或 spending limit 触顶
- 影响范围：该账户下**所有仓库所有 workflow** 一律 failure，与提交内容无关；
  历史提交重跑也一样失败

## 复现步骤

1. 前置条件：账户处于付款失败/额度耗尽状态
2. 操作或命令：推任意提交，然后
   ```bash
   gh api repos/<owner>/<repo>/actions/runs?per_page=5 \
     --jq '.workflow_runs[] | "\(.created_at) \(.name) \(.status)/\(.conclusion)"'
   ```
3. 预期结果：若代码有问题，应能看到具体 step 失败与日志
4. 实际结果：全部 `completed/failure`，但 job 没有任何 step，日志取不到

## 证据

**run 列表（实测）**：11-09 起 29 个 failure、11-10 4 个、11-11 7 个；
最后一次 success 是 `2026-11-08T06:13:23Z` —— 时间点与「代码改动」无关，是账户状态切换。

**job 字段（实测，这是判据核心）**：

```
conclusion=failure | started=2026-11-11T15:28:05Z | completed=2026-11-11T15:28:07Z
runner=（空） | labels=ubuntu-latest | steps=0
```

**日志端点（实测）**：

```xml
GET .../actions/jobs/<id>/logs
<?xml version="1.0" encoding="utf-8"?>
<Error><Code>BlobNotFound</Code><Message>The specified blob does not exist.</Message></Error>
→ gh: HTTP 404
```

**check-run annotations（实测，唯一写明原因的地方）**：

```
failure: The job was not started because recent account payments have failed
         or your spending limit needs to be increased.
         Please check the 'Billing & plans' section in your settings
```

**两条岔路（实测，别浪费时间）**：

```
GET /users/<user>/settings/billing/actions → 404 + "This API operation needs the \"user\" scope"
GET /repos/<o>/<r>/actions/permissions     → {"enabled":true,"allowed_actions":"all"}  ← 看着完全正常
```

## 根因分析

- 已确认的根因：账户级计费拦截。GitHub 照常登记 run/job 并给 `failure`，但不分配 runner、不执行 step。
- 排除过的假设：
  - 不是 workflow YAML 写错：YAML 错会在 run 层给 `startup_failure` 或带行号的 annotation，
    本轮 annotation 明确是付款文案。
  - 不是某次提交引入：**11-09 之前的提交重跑同样失败**，且多个互不相关的 workflow 一起失败。
  - 不是 Actions 被禁用：`permissions.enabled=true`。
- 问题归属：环境/账户状态，**不是代码**。

## 最小修复

代码侧无可修。要做的是**正确判定并如实标注**：

1. 取判据（三步，缺一句都别下结论）：
   ```bash
   # ① job 是否真的执行过
   gh api repos/<o>/<r>/actions/runs/<run_id>/jobs \
     --jq '.jobs[] | "\(.name)|\(.conclusion)|steps=\(.steps|length)|runner=\(.runner_name // "none")"'
   # ② 拿 SHA 对应的 check-run id
   gh api repos/<o>/<r>/commits/<sha>/check-runs --jq '.check_runs[0].id'
   # ③ 读 annotations —— 原因在这里
   gh api repos/<o>/<r>/check-runs/<check_run_id>/annotations \
     --jq '.[] | "\(.annotation_level): \(.message)"'
   ```
2. 结论只能写「**本机门禁通过，云端未验证（账户计费阻断）**」，
   不得把本机 21/21 写成「CI 全绿」。
3. 解阻需要人去 GitHub **Billing & plans** 处理付款/额度；Agent 无法绕过，也不要尝试改 workflow 去绕。

## 验证记录

- [x] 判据复现：job `steps=0`、2 秒结束、`runner_name` 空、日志 `BlobNotFound` 404
- [x] 真因取到：check-run annotation 原文为付款失败文案
- [x] 排除代码因素：11-09 前提交与多个无关 workflow 同样失败；最后成功停在 11-08
- [x] 排除「被禁用」：`actions/permissions` 返回 `enabled:true`
- [x] 本机对照：同仓库 `verify_all --profile=ci --offline` 21/21 通过 ⇒ 失败不在代码
- [ ] 云端实跑验证：**未执行**，账户计费未解阻，无法验证修复后是否转绿

## 可复用规则

1. **`enabled:true` ≠ 能跑。** 判「CI 到底跑没跑」看 job 的 `steps` 数量与 `runner_name`，
   不看 run 的 conclusion。
2. **「零 step + 秒级结束 + 无 runner + 日志 404」= 没被调度**，属账户/额度/权限层，
   不要去改代码或 workflow。
3. **失败原因优先读 check-run annotations**，run/job 对象里没有这句话；
   billing API 需要 `user` scope，普通 repo token 取不到，别在那儿绕。
4. 交付结论必须分层写：「本机可复现门禁」与「云端 CI 全绿」是两种证据，
   后者拿不到就写未验证，**不许用前者冒充后者**。

## 适用范围与不适用范围

- 适用：GitHub 免费账户 + 私有仓库；任何「全部 workflow 一起失败」的场景
- 不适用：单个 workflow 失败而其他正常（那更可能是代码/配置）；
  公开仓库 Actions 免费额度充足，一般不触发此路径

## 剩余风险

- 账户解阻后能否转绿**未验证**（见验证记录未勾项）。
- 仓库转公开后 Actions 额度规则不同，本条判据仍适用，但触发概率下降；
  本轮未实测公开后的 run 行为。

## 关联

- 相关记录：[[踩坑-ghapi带-f默认POST致探活404误判仓库已删]]（同类：API 返回码会误导，要读对字段）、
  [[踩坑-GitHub大包推送被重置需分块推送]]（同属 GitHub 侧故障分层）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码：`E:\OBsidian\全栈工程师学习资料库\09-整合任务\MS11-状态矩阵.md`（未闭合项与阻断原因记录处）
