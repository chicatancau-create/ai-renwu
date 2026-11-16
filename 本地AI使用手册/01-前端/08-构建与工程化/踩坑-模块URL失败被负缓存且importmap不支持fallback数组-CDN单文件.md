---
title: "模块 URL 失败被负缓存、importmap 不支持 fallback 数组：CDN 单文件页面的可靠加载"
date: 2026-11-15
domain: frontend
category: 01-前端/08-构建与工程化
status: verified
severity: medium
stack: [import maps, ESM, jsDelivr, unpkg, Chromium]
tags: [踩坑, CDN, 模块加载, 负缓存]
---

# 问题：单文件页面从 CDN 取 ESM，偶发 `ERR_CONNECTION_CLOSED` 后怎么都救不回来

## 一句话结论

**同一个模块 URL 失败一次就被负缓存**，同 specifier 重试必然再失败；而 **Chromium 的 importmap 不支持
fallback 数组**（写了等于整条规则失效）。可用的兜底只有三件：addon 换镜像 URL、核心失败自动重载一次、
失败面板给重试按钮——且**核心不能换源**，否则会拿到两份库实例。

## 触发条件与影响

- 项目或功能：单文件 HTML，用 importmap 从 CDN 取 three + 10 个 addon
- 环境与版本：Chromium/Edge 桌面版，`three@0.169.0`，本机出口对 `cdn.jsdelivr.net` 有 DNS 污染、对 unpkg/npmmirror DNS 超时
- 触发条件：冷启动（无缓存的 headless profile）连续拉 11 个模块文件
- 影响范围：6 次冷启动里 3 次失败，失败点还不一样（核心 / OrbitControls / OutputPass 各一次）→ 表现为"有时能开有时打不开"

## 复现步骤

1. 前置条件：一个 importmap 页面
2. 操作或命令：
   - 数组版：`"three": ["https://bad.invalid/x.js", "https://fastly.jsdelivr.net/npm/three@0.169.0/build/three.module.js"]`
   - 对照版：同一条改成单个字符串
   - 重试实验：先让主源失败，再在同一页面里 `import('three')` 重试 3 次
3. 预期结果：数组按"失败换下一个"工作；重试能救回偶发失败
4. 实际结果：数组版报 `Failed to resolve module specifier "three"`（整条规则被判无效）；
   字符串版正常；同 URL 重试 3 次全灭，**重新加载页面才通**

## 证据

- 探针文件 `_imap-test.html`（数组版/字符串版各跑一次，读页面打印结果）
- headless 日志：`net::ERR_CONNECTION_CLOSED` + `Failed to fetch dynamically imported module: .../OutputPass.js`
- 动态注入顺序的反证：控制台出现 `An import map rule for specifier 'three' was removed, as it conflicted with an existing rule`
  → 证明同一文档里**第二个 importmap 被忽略**，先注入的那份生效

## 根因分析

- 已确认的根因：
  1. 该 Chromium 版本未实现 import maps 的 fallback URL 语义，非法值导致整条 entry 被丢弃；
  2. 模块图对失败条目做负缓存，同 specifier 在本文档生命周期内永久失败；
  3. addon 内部 `import 'three'` 走 importmap，所以核心一旦改源就会与 addon 用的核心形成两份实例。
- 排除过的假设：不是 URL 写错（同 URL 下次冷启动就成功）；不是 CORS（jsDelivr 带 `ACAO: *`）
- 问题归属：环境或依赖

## 最小修复

1. importmap 静态写死一个主源（`fastly.jsdelivr.net`）。
2. addon 逐个包一层：`try import(bare)` → 失败则遍历镜像列表 `import(绝对URL)`。
3. 核心失败 → `sessionStorage` 打标 + `location.reload()` **一次**，启动成功后清标。
4. 仍失败 → 错误面板显示原始报错 + 「重新加载」按钮 + 一句"把域名换成 unpkg.com 或本地 three 构建"。
5. 若坚持动态选源：注入必须由**普通 classic script** 完成且排在静态 map 之前——
   内联 `<script type="module">` 自身已触发模块加载，那时注入会被忽略并报
   `added after module script load was triggered`。

## 反效果（本次先犯后改）

用**同步 XHR 探测镜像可达性**再动态注入 importmap：本机 unpkg/npmmirror 的 DNS 直接超时（curl 也 8s 超时），
同步阻塞把首屏拖慢十几秒；而 HEAD 探测在浏览器里还可能全灭（curl 拿 200，浏览器 XHR 拿不到状态码），
探测结果恒为 null。**别在主线程同步探测网络。**

## 验证记录

- [x] 探针实验：数组版失败 / 字符串版成功（同页对照）
- [x] 端到端：加上 addon 换镜像 + 核心自动重载后，连续冷启动全部成功（一次靠自动重载、一次靠换镜像）
- [x] 首屏耗时：删掉同步探测后由 19–54s 回落到 10–30s
- [ ] 构建 / 类型检查 / 单元测试：本任务无这些环节，未执行

## 可复用规则

给"单文件 + CDN ESM"的交付做加载兜底时，按这个顺序写：**静态主源 → addon 换镜像 → 核心重载一次 → 人工重试按钮**。
不要在浏览器里做同步网络探测，不要指望同 URL 重试，不要把核心指向与 importmap 不同的源。
例外：如果页面允许离线运行，直接内联/本地化依赖，比任何镜像策略都可靠。

## 适用范围与不适用范围

- 适用：无构建、单文件、走 CDN 的 ESM 页面；国内网络出口不稳的交付
- 不适用：有打包器的工程（构建期就固定了源）；Safari/Firefox 的 importmap 语义未测

## 剩余风险

- 出口被完全封死时仍需人工换域名。
- 未验证 `<link rel="modulepreload">` 与 Service Worker 缓存能否进一步降低抖动概率。

## 关联

- 相关记录：[[踩坑-隐藏页挂起rAF且截图字节数判不了黑屏-WebGL取证]]、[[踩坑-虚拟网卡空metric抢走默认路由致域名假超时]]
- 相关分类：03-通用/03-调试与验证
- 相关代码：`E:\fullstack-code\Web\webgl自学\浮空树脂小岛.html`（`imp()` 与启动块）
