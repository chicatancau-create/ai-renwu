---
title: "headless Edge 可跑 WebGL 全速渲染且无垂直同步，CDP 验收打法"
date: 2026-11-16
domain: frontend
category: 测试验收
status: needs-review
severity: low
stack: [Three.js, Edge, CDP, Node]
tags: [headless, WebGL, Three.js, 验收, 垂直同步]
---

# 规则：headless Edge 跑 Three.js/WebGL 页的验收要点

> `needs-review`：仅在 Edg/157.0.4341.60 + 一个 ~9.4k 体素场景上实测一次，未跨版本复验。

## 一句话结论

单文件 Three.js 页可以直接用自启 headless Edge（不传 `--disable-gpu`，加 `--enable-unsafe-swiftshader`）做 CDP 全量验收，软件渲染能全速跑；但 headless 无垂直同步，帧率数字与真机体验无关，断言只能用相对基线倍率。

## 触发条件与影响

- 项目或功能：单文件 Three.js 体素场景（InstancedMesh ~9.4k 方块 + 2048 shadow map）交付后验收
- 环境与版本：Windows + Edg/157.0.4341.60 `--headless=new`，Node 24 全局 WebSocket 手写 CDP 客户端
- 触发条件：3D 页面需要「真渲染 + 可交互」取证，零 CDP 命令行回路（`--screenshot`）覆盖不了交互
- 影响范围：WebGL 页的运行时验收；不涉及真机画质结论

## 复现步骤

1. 前置条件：页面经本地静态服务（`srv.listen(0)`）或 file:// 打开
2. 操作或命令：spawn `msedge --headless=new --remote-debugging-port=0 --user-data-dir=<临时> --enable-unsafe-swiftshader --hide-scrollbars`，端口只从自有 profile 的 `DevToolsActivePort` 读
3. 预期结果：WebGL 上下文创建成功、rAF 循环推进、可注入断言
4. 实际结果：~9.4k 体素 + 2048 阴影在 1440×900 稳定 ~300 fps，全程无页内异常；CDP `Input.dispatchMouseEvent` 拖拽/滚轮能真实驱动 canvas 相机

## 证据

- `Browser: Edg/157.0.4341.60`；frameCount 采样 2s 差值 ≈ 300/301/302（三轮一致）
- 拖拽后 cameraPos 变化 44.4；滚轮 dist 62→23.8；27 项断言全绿（2026-11-16，Web/HTTP 浮空御园交付）
- Three.js CDN：fastly.jsdelivr 直连成功，四级回退链未触发

## 根因分析

- 已确认：headless=new 默认走软件渲染仍可建 WebGL 上下文；headless 无垂直同步导致 rAF 无上限
- 未测（不要当结论）：传 `--disable-gpu` 是否致命；`--enable-unsafe-swiftshader` 缺省时是否自动回退
- 问题归属：环境或依赖（headless 特性），非页面缺陷

## 可复用规则

1. WebGL 页验收 flag 组合：`--headless=new --remote-debugging-port=0 --enable-unsafe-swiftshader`，**别带 `--disable-gpu`**。
2. 页面侧预埋只读调试钩子（如 `window.__garden` 暴露 cameraPos/state/frameCount/drawCalls），交互断言才有落点；交付文件保留无副作用。
3. 帧率断言写「相对基线倍率」（如 0.4×–1.8× baseline）判停摆/重复循环，**不写绝对上限**——300 fps 是 headless 特性不是页面性能。
4. 移动端视口用 `Emulation.setDeviceMetricsOverride`（真 390px），与零 CDP 回路 `--window-size` 的假视口结论不可互串。
5. CDN 引入用四级回退动态 import（fastly.jsdelivr → cdn.jsdelivr → npmmirror → unpkg），验收时资源类 console 报错单独归类，不与脚本错误混判。

## 适用范围与不适用范围

- 适用：单文件/静态 Three.js 等 WebGL 页的「能跑、交互通、控件联动」验收。
- 不适用：真机画质/光照/色调映射结论（软件渲染截图与真 GPU 有差）；Chrome 扩展场景（另有 Edge 优先规则）。

## 剩余风险

仅验证一个 Edge 版本与一个场景规模；`--disable-gpu` 行为、Chrome 是否同样可用未测。

## 关联

- 相关记录：99-收件箱 内其余验收类条目；外部：QoderToolkit `headless-cdp-visual-acceptance` 技能（DOM/CSS 断言，本条补 WebGL 缺口）
- 相关分类：01-前端 / 03-通用
- 相关代码：验收脚本已随临时目录清理，要点全部在本条
