---
title: "隐藏页挂起 rAF、截图字节数判不了黑屏：WebGL 页面取证套路"
date: 2026-11-15
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [WebGL, Three.js, Chrome DevTools Protocol, headless Edge]
tags: [验证, 取证, rAF, readPixels]
---

# 问题：WebGL/动画页面在连接器浏览器里"永远卡在 loading"，且黑屏判据不可靠

## 一句话结论

**隐藏页面不产帧**（rAF 被挂起），所以任何依赖动画循环的页面在连接器 tab 里必然看着像卡死；
而**截图字节数、隐藏页里的 `readPixels` 都不能用来判"是不是黑屏"**——要像素证据必须自己起 headless 浏览器。

## 触发条件与影响

- 项目或功能：单文件 three.js 实时 3D 页面（首帧由 `requestAnimationFrame` / `setAnimationLoop` 驱动）
- 环境与版本：Qoder 连接器浏览器（browser-use，Chromium 系）、本机 headless Edge、Node 24
- 触发条件：用连接器 tab 打开页面做验收；或用截图文件大小判断渲染是否成功
- 影响范围：会把"取证通道不可用"误判成"应用有 bug"，进而误改代码；也会把"全黑"和"有内容"判反

## 复现步骤

1. 前置条件：一个首屏靠 rAF 才消失 loading 遮罩的 WebGL 页面
2. 操作或命令：连接器 tab 里 `navigate_page` 后轮询 loading 元素；再跑 rAF 探针
3. 预期结果：几秒内遮罩消失、开始出帧
4. 实际结果：遮罩永不消失；探针返回 `{"vis":"hidden","hidden":true,"raf":"raf-BLOCKED","ctxLost":"ok"}`
   —— WebGL 上下文正常，只是不进帧。同一页在自起 headless Edge 里 10–30s 正常启动。

## 证据

- rAF 探针（一次调用可确诊）：

  ```js
  const p = new Promise(res => { let d = false;
    requestAnimationFrame(() => { d = true; res('raf-fired'); });
    setTimeout(() => { if (!d) res('raf-BLOCKED'); }, 2500); });
  return JSON.stringify({vis: document.visibilityState, raf: await p});
  ```

- 隐藏页里 `gl.readPixels` 三次全 0（实际有画面）→ 会得出假"全黑"。
- 截图字节数反例：全黑 + DOM 覆盖层的帧 380KB；正常渲染的帧 1.1MB；纯黑无覆盖层约 2KB。大小不可比。
- headless 命令（本机有独显，走真 GPU，别默认软件光栅）：

  ```
   msedge --headless=new --remote-debugging-port=0 --user-data-dir=<tmp>
          --enable-unsafe-swiftshader --disable-backgrounding-occluded-windows
          --disable-renderer-backgrounding --window-size=1280,800
  ```

## 根因分析

- 已确认的根因：浏览器对 hidden 页面节流/挂起 rAF；`readPixels` 在没有合成帧时读到空缓冲；
  PNG 大小由**整张截图**（含 DOM）决定，与 WebGL 画布内容无关。
- 排除过的假设：① WebGL 上下文丢失（`isContextLost()` 返回 false）；② 模块没加载完（初始化代码已跑完）；
  ③ 页面报错（console 与异常收集为空）。
- 问题归属：环境或依赖（取证通道），不是被测代码

## 最小修复

不改被测代码，改取证通道：

1. 端口从 `<profile>/DevToolsActivePort` 第一行读，**绝不连固定调试端口**（Qoder 自己的 headless 占着 9333，连上去会操作用户的标签页）。
2. Node 24 有全局 `WebSocket`，几十行裸写 CDP 即可：`Page/Runtime/Log.enable` →
   `Emulation.setDeviceMetricsOverride` → `Page.navigate` → `Page.captureScreenshot`。
   视口只用 `Emulation.setDeviceMetricsOverride`；CLI 的 `--window-size` 会被夹到最小宽度后裁图。
3. `/json/list` 混着扩展的 `background_page`，取 `type === 'page'`。
4. 定量判黑就在**可见/headless 页内** `readPixels` 算均值 + 非黑像素占比，或直接看图。
5. 收尾 `taskkill /PID <pid> /T /F` + 删临时 profile，否则每次验证留一个目录。

## 验证记录

- [x] 静态检查：`node --check` 通过（页面模块脚本）
- [x] 启动或手动回归：headless 打开 → boot 遮罩移除 → 三档光照截图正常 → 异常收集为空
- [x] `file://` 直开（中文路径 + 百分号编码）同样可跑：title 正确、canvas 存在、约 20s 后遮罩移除、无 console 报错
- [ ] 类型检查 / 构建 / 单元测试：本任务无这些环节，未执行

## 可复用规则

验动画或 WebGL 页面时，**第一步先测 `document.visibilityState` + rAF 探针**；
只要 `raf-BLOCKED` 就立刻换自起 headless，不要继续在被测代码里找 bug。
判"是否黑屏"只承认两种证据：页内 `readPixels` 均值（可见页）或人眼看图；**文件大小一律不作判据**。
例外：纯 DOM 页面不受影响，连接器 tab 仍可做结构断言（snapshot、evaluate、fill、click）。

## 适用范围与不适用范围

- 适用：本机所有需要像素证据的前端/图形/动画验证；任何 rAF 驱动的页面
- 不适用：纯静态 DOM 验收；Safari/Firefox（未测）；无独显机器上 `--enable-unsafe-swiftshader` 的耗时（未测）

## 剩余风险

- 无 GPU 机器上 headless 可能退回软件光栅，首帧耗时量级完全不同，阈值要重估。
- 未验证 `--window-size` 与 device metrics 同时使用时的优先级。

## 关联

- 相关记录：[[踩坑-模块URL失败被负缓存且importmap不支持fallback数组-CDN单文件]]、
  [[踩坑-反向smoothstep吐NaN经Bloom放大成整帧黑-WebGL]]
- 相关分类：01-前端/08-构建与工程化、01-前端/03-JavaScript与TypeScript
- 相关代码：`E:\fullstack-code\Web\webgl自学\浮空树脂小岛.html`（2026-10-19 实测载体）
