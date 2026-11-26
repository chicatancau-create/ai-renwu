---
title: "uni-app H5 刷新指示器靠绝对定位隐藏 + reload 未重置 pageIndex：分页取证两坑"
date: 2026-11-18
domain: frontend
category: 调试与验证
status: verified
severity: medium
stack: [uni-app Vue2, HBuilderX 4.36, Chrome 157 headless, CDP chrome-remote-interface]
tags: [uni-app, 下拉刷新, 分页, CDP, headless, 取证判据]
---

# 问题：uni-app H5 分页下拉刷新取证误判（指示器隐藏机制 + 页码未重置）

> `verified` 范围＝取证判据与隐藏机制已复现、定位、修正判据并重跑全绿；应用缺陷（reload 未重置 pageIndex）已定位但**未修**（本轮任务为只读取证），见「最小修复」「剩余风险」。

## 一句话结论

CDP 取证 uni-app H5 分页下拉刷新时，用 display/height 判「指示器已停止」必假阳性（`uni-page-refresh` 是 position:absolute，停止时被移到视口上方，rect.bottom<0 而 display/height 不变）；同时业务 `reload()` 只把请求参数置 0、不重置 `this.pageIndex`，刷新后首次触底请求旧索引+1（实测 5），跳过中间页——前者是取证判据问题（已修正重跑全绿），后者是应用缺陷（已定位；业务方 2026-11-18 修复并回归绿）。

## 触发条件与影响

- 项目或功能：`E:\fullstack-code\跨平台应用开发\wofule` 的 `pages/comment/commentlist`（食物评论列表；pages.json:34-39 开 enablePullDownRefresh、onReachBottomDistance:50）
- 环境与版本：HBuilderX 4.36.2024112612-alpha cli launch web；dev 新实例 8081（8080 被旧实例占用）；Chrome 157 `--headless=new`；CDP 宽 450（Emulation.setDeviceMetricsOverride）
- 触发条件：onReachBottom 连续加载多页后调 `uni.startPullDownRefresh()`，再触发一次触底
- 影响范围：取证脚本误判刷新未停止；应用刷新后列表停 10 条且永远跳不到中间页

## 复现步骤

1. 前置条件：后端 `:8090/foodapp/comments/getCommentsByFoodIdByPage`，body `{foodid,pageIndex,pageSize}`（参数名是 **pageIndex**，传 `page` 报 HTTP 500）；总 39 条＝10+10+10+9
2. 操作或命令：`window.scrollTo(0,document.body.scrollHeight)` ×4（每次等 ≥2s，含 showLoading+setTimeout1000）→ 20/30/39/39；页内 `uni.startPullDownRefresh()`；每 100ms 采样 `uni-page-refresh`；再 scrollTo 触底
3. 预期结果：刷新后卡片回 10 且指示器消失；下次触底请求 pageIndex:1
4. 实际结果：卡片回 10 ✓；指示器 display:block、height:40 不变但 rect top:-239/bottom:-199（视口外）；下次触底请求 **pageIndex:5**，count 停 10

## 证据

- `C:\Users\Admin\iconpark-render\verify7.json`：apiCalls postData 序列 0,1,2,3,4 → refresh 0 → **5**；refresh.after `{position:absolute, top:-239, bottom:-199, height:40, display:block}`；15 个采样 rect 判据全 false
- 截图 `verify7-comment-1/2/3.png`（450×900）：10 卡 / 39 条尾部 / 刷新后 10 卡无 spinner
- 脚本 `C:\Users\Admin\iconpark-render\verify7.mjs`（Network pending _idle 等待、:8090 postData 捕获、rect 判据）
- top:-239 来源：列表缩到 10 条后 scrollHeight 1139 − innerHeight 900 = 239，浏览器把 scrollY 从 3255 clamp 到 239，文档顶部的 absolute 元素 rect.top 随之 = -239
- postData:null 的条目是 CORS 预检 OPTIONS，不是缺参数

## 根因分析

- 已确认的根因 1（取证判据）：`uni-page-refresh` 靠绝对定位移出视口隐藏，display/height 不变 → 判据必须 `getBoundingClientRect().bottom > 0`（或 top>=0）+ 截图对照
- 已确认的根因 2（应用缺陷）：`commentlist.vue:38` reload() 只在请求体写 `pageIndex: 0`（:47），不重置 `this.pageIndex`；`:64` loadmore() 对旧值 `this.pageIndex + 1` → 刷新后首请求 5。onLoad :22 有置 0，但 onPullDownRefresh :25-26 直调 reload() 绕过了它
- 排除过的假设：指示器没停（截图无 spinner）；onPullDownRefresh 没触发（refresh 阶段 pageIndex:0 请求为证）；后端分页错（直连探针 page0..4 = 10/10/10/9/0）
- 问题归属：判据问题＝本次取证脚本引入（已修）；pageIndex 缺陷＝修改前已有

## 最小修复

- 取证判据：verify7.mjs 的 refreshVisible 改 `rect.bottom > 0` 并记录 top/position/transform；重跑全绿
- 应用缺陷：本轮只读取证未修、已回报；业务方随后授权修复，于 reload() 首行补 `this.pageIndex = 0`（commentlist.vue:39），verify8 回归全绿（见验证记录）

## 验证记录

- [x] 单元、集成或端到端测试：CDP 重跑（8081）initial 10 → 20/30/39/39 → refresh 回 10 + 指示器视口外；console/exception/netfail 全 []；scrollW=clientW=450
- [x] 启动或手动回归：三张截图目视（10 卡 / 39 尾 / 刷新后无 spinner）
- [x] 修复回归：业务方 2026-11-18 补 commentlist.vue:39 `this.pageIndex = 0`；verify8（8081）全绿：post-refresh 触底请求序列 **1,2**（缺陷期为 5,6）、卡数 20→30、refresh 请求 0、errors []；证据 `C:\Users\Admin\iconpark-render\verify8.json` / `verify8-refresh-then-more.png`
- 格式化/类型/构建：不适用（未改项目）

## 可复用规则

- 判 H5 下拉刷新指示器状态看**内层 `div.uni-page-refresh` 的 display（none＝已停，v-show）**或外层 wrapper rect 出视口（bottom<=0）；外层 wrapper 是 position:absolute 且 display/height 恒不变，**scrollY=0 时停止态 rect 仍 0..40**，单用 `rect.bottom>0` 会在零滚动位假判「在显示」（verify11 实测：内层 display:none + wrapper rect 0..40 + 截图无 spinner）；务必截图对照。适用 uni-app H5；原生端/其他框架先实测
- 分页刷新取证必抓请求体序列（CDP Network.requestWillBeSent postData）：refresh 应回 0、下一页应为 1；出现旧索引+1＝前端没重置页码。postData:null 是预检 OPTIONS
- H5 onReachBottom 可用 `window.scrollTo(0,document.body.scrollHeight)` 触发（阈值 onReachBottomDistance）；页面带 showLoading+setTimeout 时每次触底等 ≥ delay+网络+渲染
- 列表缩短后 scrollY 被浏览器 clamp（scrollHeight−innerHeight），absolute 元素 rect 随之偏移，别误读成「元素自己动了」
- clamp 产生的 scroll 事件会自动触发 onReachBottom（verify7 刷新期那条 pageIndex:5 即此路径）；取证「刷新后页码序列」前先 scrollTo(0,0) 隔离
- 截「N 卡列表底部」又不想再触发触底加载：Page.captureScreenshot({clip:{y:scrollHeight−视口高}, captureBeyondViewport:true})，不产生 scroll 事件
- 内容不足一屏时 body.scrollHeight 被视口高兜底（sh==ih），scrollTo(0,scrollHeight) 不产生滚动→onReachBottom 不触发；短列表取证触底要按真实内容底（列表容器 rect.bottom）设更矮视口（内容底−60），刷新后重算（verify9：内容底 184→视口 124 才触发）
- CDP 端口所有权判据要防 IPv6 退听：chrome bind 失败会改听 ws://[::1]:<port>，只 grep 127.0.0.1 会假阴性 abort；先查 Listen 表确认端口空闲（本机 9230 被 DSH 主进程占），再按日志实际地址匹配（verify9 run1 教训）

## 适用范围与不适用范围

- 适用：uni-app Vue2 H5 + headless Chrome CDP 取证；Spring 式 Page 分页后端
- 不适用：uni-app 原生/App 端刷新指示器 DOM 结构；其他 UI 框架的 refresh 组件

## 剩余风险

- 应用缺陷已修并回归（2026-11-18 verify8）。残余框架行为：刷新时若停在列表底部，scrollY clamp 的 scroll 事件会自动触发一次 onReachBottom（非缺陷）；取证刷新序列前先回顶隔离
- 仅 Chrome 157 headless + 宽 450 实测；指示器可见窗口 <100ms 未被采样捕获（不影响「已停止」判定）

## 关联

- 相关记录：[[踩坑-tabBar的list写成重复对象键致loader崩且截图视口不符会误判少一个tab]]、[[03-通用/03-调试与验证/经验-课件截图反推rpx先按分隔线间距定标-uni-app|课件截图反推 rpx]]
- 相关分类：03-通用/03-调试与验证
- 相关代码、命令或文档：`E:\fullstack-code\跨平台应用开发\wofule\pages\comment\commentlist.vue:22,25-26,38,47,63-64,73`；`pages.json:34-39`；证据 `C:\Users\Admin\iconpark-render\verify7.mjs / verify7.json / verify7-comment-1..3.png`