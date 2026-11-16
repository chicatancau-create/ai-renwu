---
title: "牛客 robots 禁 /search：采集只能走 sitemap，且正文必须渲染才拿得到"
date: 2026-11-15
domain: common
category: 04-工程规范与安全
status: verified
severity: high
stack: [Node 24, CDP, Edge headless, curl, Python]
tags: [爬虫合规, robots, sitemap, SPA, 渲染取证, 假阳性匹配]
---

# 问题：用站内搜索找帖子做采集，写完才发现 robots 明令禁止；且 curl 拿到的 HTML 里根本没有正文

> 事发 2026-11-12，2026-11-15 回写。

## 一句话结论

`nowcoder.com/robots.txt` 明确 `Disallow: /search`，**用搜索页找候选帖就是违规**；
合规入口是它自己公布的 `sitemap1.txt` / `sitemap2.txt`。
另外该站是 SPA：**原始 HTML 只有 6 KB 外壳，正文靠客户端渲染**，
`curl` 抓到的字节里没有题目文本，必须用无头浏览器取 `document.body.innerText`。
盲试 `/api/...` 路径没有意义——SPA 对未知路径一律回 200 + HTML 外壳。

## 触发条件与影响

- 项目或功能：为题库逐题补「原始面经」证据，需要公开可访问的帖子 URL + 可核对的原文引文
- 环境与版本：Windows；Node v24（自带 WebSocket，无需 ws 包）；Edge headless + CDP
- 触发条件：先写采集器再查 robots；或只用 `curl` 判断「页面有没有内容」
- 影响范围：第一版采集器已跑了多轮搜索页抓取，属于**事后才发现的合规违规**，必须停任务、改通道、重跑

## 复现步骤

1. 前置条件：目标是牛客公开讨论帖
2. 操作或命令：
   ```bash
   curl -s https://www.nowcoder.com/robots.txt
   curl -s -A "<桌面 UA>" https://www.nowcoder.com/discuss/<id> -o page.html
   grep -c '二叉树路径总和' page.html
   ```
3. 预期结果：robots 允许搜索；HTML 里能 grep 到帖子正文
4. 实际结果：robots 写着 `Disallow:/search`；HTML 只有 **6282 字节**，关键词命中 **0**

## 证据

**robots.txt 原文（实测）**：

```
User-agent:*
Disallow:/search
Disallow:/nccommon
Disallow:/ab/ab-test-flow
Sitemap:https://www.nowcoder.com/sitemap.xml
Sitemap:https://www.nowcoder.com/sitemap.txt
...
```

`sitemap.txt` 只有 111 字节，是个索引，真正的内容在它列出的两个文件里：

```
sitemap1.txt  1,001,745 bytes → 10,975 条 /discuss/<id>
sitemap2.txt     56,264 bytes →    605 条 /feed/main/detail/<id>
去重合计 11,580 条，URL 自带 ?urlSource=sitemap 标记
```

**SPA 外壳判据（实测同一 URL 两种取法）**：

```
curl 原始 HTML : 6282 bytes，grep '二叉树路径总和' = 0，grep 'Leetcode' = 0
headless 渲染后: document.body.innerText 长度 5390，完整列出
                 "10、Leetcode112. 二叉树路径总和 https://leetcode.cn/problems/path-sum/"
```

**盲试 API 的无效性（实测）**：

```
/api/discuss/search?query=...        → 200，但内容是 <!DOCTYPE html> SPA 外壳（19262 bytes）
/np-api/simple/search/discuss?...    → 404，JSON 错误体（说明 /np-api 是真后端，但路径靠猜不可行）
```

**预筛命中率与并发收益（实测）**：

```
抽样 120 条标题 → 14 条含目标公司名（约 12%）
串行 8 并发 + 每批 sleep 300ms → 25 分钟仍未跑完 11580 条，被迫中止
改 24 并发 + 无间隔 + 标题缓存落盘 → 约 2 分钟跑完全量
```

## 根因分析

- 已确认的根因：
  1. 合规层面——站点用 robots 明确禁了搜索路径，采集器却以搜索页为候选来源。
  2. 技术层面——SPA 首屏只返回外壳，正文由前端 JS 拉取渲染；`curl` 停在第一跳。
- 排除过的假设：
  - 不是反爬拦截：同一 URL 渲染后能拿到完整正文，且无登录墙标记。
  - 不是 UA 问题：换桌面 UA 后原始 HTML 仍是 6 KB 外壳。
- 问题归属：本次采集器设计引入（先写后查合规），不是站点故障。

## 最小修复

1. **动手前先取 robots**，把 `Disallow` 列表当硬约束；候选来源只用站点自己公布的 sitemap。
2. 候选发现与正文抓取**分两层**：
   - 第一层用 `curl` 批量取 `<title>` 做预筛（便宜、可并发、可缓存）；
   - 第二层只对预筛命中的 URL 启动 headless 渲染取 `innerText`（贵，别全量渲染）。
3. 标题缓存落盘（URL → title 的 JSON），换关键词/换目标复跑时不重扫；缓存可从 sitemap 重建，不入库。
4. 遇到登录墙 / 仅作者可见 / 内容已删除 → 记 `blocked` 并停止，**不绕过、不猜 URL**。
5. 并发要够：`Promise.all` 批 24、批间不 sleep，比 8 并发 + 300ms 快一个数量级。

## 验证记录

- [x] robots 实取：确认 `Disallow:/search`，并拿到 sitemap 索引链
- [x] 通道改造后跑通：sitemap 11,580 条 → 标题预筛 → 渲染深抓，产出可核对引文
- [x] 渲染必要性证实：同一 URL curl 命中 0 / 渲染命中完整题目行
- [x] 违规通道已停用：搜索页抓取代码整段删除，任务中止后未再访问 `/search`
- [x] 结果经人工逐条复核：16 条证据全部核对引文与题号一致；链接复验 16/16 PASS
- [x] 门禁：题库结构门禁 6/6、全仓 `verify_all --profile=ci --offline` 21/21

## 可复用规则

1. **任何采集任务的第一条命令是取 robots.txt**，不是写选择器。写完再查等于已经违规。
2. 判「页面有没有内容」不能只看 `curl` 的字节数：**SPA 外壳也是 200**。
   判据是「目标关键词在原始 HTML 里能否 grep 到」，grep 不到就必须渲染。
3. 不要盲试 JSON API 路径：SPA 站对未知路径回 200 + HTML，`/np-api` 这类真后端会回 404 JSON，
   两者都不构成「找到了接口」。**用站点公布的 sitemap / 公开列表页**。
4. 字符串匹配当证据判定时，必须加三道闸（本轮踩全）：
   - **边界**：`valid-parentheses` 是 `longest-valid-parentheses` 的子串 → slug 必须整段匹配；
   - **互斥**：同一行出现别的题号（`Leetcode 212 单词搜索`）就不能算本题（79）；
   - **语境**：`平衡二叉树` 出现在 STL 讲解里不算考题，要求同行有「手撕/算法/题目」等字样。
   另外要排除**非目标内容**：博客链接合集、多公司合辑帖、同文重复发帖（按正文指纹去重，
   且指纹只能取问答正文——侧栏推荐与浏览数每次都不同，会让去重失效）。
5. 覆盖率数字必须与统计脚本一致，**聚合来源不得写成已核验**。

## 适用范围与不适用范围

- 适用：牛客及同类 SPA 社区站的公开内容采集；任何「先找候选再取正文」的两层抓取
- 不适用：需要登录才能看的内容（一律停止）；有官方 API 且条款允许的场景应优先用 API

## 剩余风险

- sitemap 只覆盖站点愿意公开的部分，**产量有上限**：本轮 153 次尝试只成 16 条，
  剩 237 题仍无原始证据。想再提升需换通道，且换通道前要重新确认条款。
- 命中率依赖标题含公司名，标题不规范的帖子会被预筛漏掉（已知取舍，非缺陷）。
- 站点随时可能改 robots 或 sitemap 结构，**每次任务都要重取**，不能沿用本条记录里的数字。

## 关联

- 相关记录：[[踩坑-GitHub大包推送被重置需分块推送]]（同类：外部服务行为要实测不能假设）
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码：`E:\OBsidian\全栈工程师学习资料库\08-判定题库\国内大厂真题\_工具\collect_interview_evidence.mjs`
  （采集器，提交 `8d699aa`；渲染器复用 `06-实验代码\_shared\headless.mjs`）
