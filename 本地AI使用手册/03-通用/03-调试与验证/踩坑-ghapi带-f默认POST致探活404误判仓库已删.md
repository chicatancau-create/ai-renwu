---
title: "gh api 带 -f/-F 默认变 POST：探活 404 险些误判仓库已删，列仓库竟成建仓库请求"
date: 2026-11-12
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [GitHub CLI, gh, PowerShell 5.1]
tags: [gh api, POST, 探活, 误判, 副作用]
---

# 问题：用 gh api 做只读探活，加了 -f 参数后请求悄悄变成 POST

## 一句话结论

`gh api` 一旦带 `-f`/`-F` 字段参数，默认方法就从 GET 变 **POST**。拿它探活会把「读」变成「写」：
`POST /repos/{owner}/{repo}/commits` 回 **404**，看起来和「仓库被删」一模一样；
`POST /user/repos` 则是**创建仓库**请求。**探活/列举必须显式 `-X GET`**（或把参数写进 URL query）。

## 触发条件与影响

- 项目或功能：2026-11-12 检查本机两个 git 账号时，用 gh api 验证 GitHub 仓库存在性与账号仓库清单。
- 环境与版本：GitHub CLI（gh）+ Windows PowerShell 5.1。
- 影响范围：轻则误判「仓库已删/账号异常」，重则往账号里创建垃圾仓库（本次被参数校验拦下）。

## 复现步骤与证据（报错原文）

1. `gh api repos/chicatancau-create/fullstack-code/commits -f per_page=1`
   → **HTTP 404 Not Found** —— 险些据此下结论「仓库已删」。
2. `gh api user/repos -f per_page=100`
   → **HTTP 422** `"New repository name must not be blank"`（documentation_url 指向 create-a-repository）
   —— 报错体暴露请求真身：`POST /user/repos` = 建仓库。因缺 name 被拒，**未创建任何东西**。
3. 显式 GET 纠正后：`gh api repos/chicatancau-create/fullstack-code -X GET` → 200，
   `private:true`、`pushed_at 2026-11-09T13:15:53Z`，仓库好好的；
   `gh api user/repos -X GET` → 7 个仓库（cc-hud、CodeWeave、folia-major、fullstack-code、
   fullstack-study-library、learning-blog-demo、super-productivity），与 422 之前比对无新增
   → 证实那次 POST 确实零残留。

## 根因分析

- 已确认的根因：gh api 的方法推断规则——带 `-f`/`-F` 且未显式 `-X` 时默认 POST（gh 的文档化行为，不是 bug）。
- 排除过的假设：不是仓库被删、不是令牌失效、不是网络问题——同一令牌显式 GET 全部 200。
- 问题归属：工具用法。404 是「POST 打到只读端点」，不是「资源不存在」。

## 最小修复

探活/列举一律显式 `-X GET`；分页等参数改放 URL query（`?per_page=1`）也可避开方法推断。

## 验证记录

- [x] 两种错误形态各复现一次（404 / 422 原文见上）。
- [x] `-X GET` 纠正后仓库存在、清单完整、前后比对无副作用残留。

## 可复用规则

用 gh api 做「探活/存在性/列举」时：
① 永远显式 `-X GET`；② 见到 404 先怀疑**请求方法被参数改写**，再下「资源不存在」的结论；
③ 422 参数校验错是「请求打到了写端点」的信号，立刻停手核对方法。
与「探测方式自己造出假结论」同族：credential fill 回显密钥、push --dry-run 删凭据、路由探针拿错 UA 造假故障。

## 适用范围与不适用范围

- 适用：一切 gh api 调用（GitHub 及任何兼容端点）。
- 不适用：本来就要 POST 的创建类操作——但那也应显式写 `-X POST`，别靠默认推断。

## 剩余风险

未发现已知剩余风险；gh 升级若改默认行为需重测（易变项用前实测）。

## 关联

- 相关记录：[[踩坑-Gitee仓库401分不清缺凭据还是缺权限且fill探测会回显密钥]]、
  [[踩坑-路由熔断红标是历史失败且探针自身会造假故障]]、
  [[踩坑-按URL子串判读写致register被当读端点探测时写入用户库]]、
  [[规则-GitCode令牌只读活验用api-v5用户端点]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
