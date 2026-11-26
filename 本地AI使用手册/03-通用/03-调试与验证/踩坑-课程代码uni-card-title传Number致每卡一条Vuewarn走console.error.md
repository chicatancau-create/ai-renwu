---
title: "课程代码 uni-card :title 传 Number：每卡一条 Vue prop warn 走 console.error，「console 全[]」验收假红"
date: 2026-11-18
domain: frontend
category: 调试与验证
status: verified
severity: medium
stack: [uni-app Vue2, uni-card, HBuilderX 4.36, Chrome 157 headless, CDP]
tags: [Vue warn, console.error, uni-card, prop类型, 验收判据, 落盘竞态]
---

# 问题：uni-card title prop 为 String 而课程代码传 Number，Vue warn 以 console.error 发出致全绿验收失败

> `verified`：复现、定位、修复（业务方 `+''` 强转）、修复回归（verify11b 13/13 全绿）均完成，2026-11-18。

## 一句话结论

Vue2 dev 模式的 prop 类型警告经 **console.error** 发出：课程 14start 代码 `:title="item.userId"` 传 Number 22，而 uni-card 的 title prop 声明 String，于是每张卡每个渲染轮各一条 `[Vue warn]: Invalid prop…`，使「console error/warning 全 []」验收必红（verify11 实测 40 条＝10+10+20）；渲染本身正常（标题仍显示 22）。修复为课程 14work 原写法 `:title="item.userId+''"`，落盘后 verify11b 复跑 13/13 全绿、errors []。

## 触发条件与影响

- 项目或功能：`E:\fullstack-code\跨平台应用开发\wofule` 的 `pages/comment/commentlist`（照课程 14start 重写版）
- 环境与版本：dev 8080（HBuilderX 4.36 watch）；Chrome 157 `--headless=new`；CDP 宽 450
- 触发条件：任何渲染 uni-card 列表的轮次（onLoad reload / 下拉刷新 / 触底 concat）
- 影响范围：验收脚本 errorsEmpty 假红；功能无影响（仅警告，标题正常渲染）

## 复现步骤

1. 前置条件：后端 `:8090/foodapp/comments/getCommentsByFoodIdByPage` 返回 `userId=22`（Number）
2. 操作或命令：开 `#/pages/comment/commentlist?foodid=1` → `uni.startPullDownRefresh()` → 触底；CDP `Runtime.consoleAPICalled` 收集 type=error/warning
3. 预期结果：console error/warning 全 []
4. 实际结果：修复前 load/refresh/reach 三相各 10/10/20 条同文 warn；修复后 0 条

## 证据

- `C:\Users\Admin\iconpark-render\verify11.json` errors 数组 40 条，原文：`[Vue warn]: Invalid prop: type check failed for prop "title". Expected String with value "22", got Number with value 22.` found in `<UniCard> at uni_modules/uni-card/components/uni-card/uni-card.vue at pages/comment/commentlist.vue`
- `C:\Users\Admin\iconpark-render\verify11b.json`：修复落盘（commentlist.vue mtime 2026-11-18 16:51:31）后复跑，assertions 13/13 true、errors []；截图 verify11-comment.png / verify11-after-refresh.png 已覆盖（渲染与修复前字节级同 sha 07bdddd9，证明 `+''` 不改渲染）
- **落盘竞态假红**：verify11b 首跑（约 16:51:0x）早于落盘 16:51:31，磁盘 grep 仍见旧 `:title="item.userId"`、运行仍 40 warn；落盘后二跑全绿。判「修复是否生效」以磁盘源码+mtime+复跑为准，不以口头「已改」为准
- 截图（450×900）：卡面标题 22 正常、无 footer——本版 uni-card **无 note prop**（grep 零命中），页面 `note="Tips"` 落为根元素 attribute，故 innerText 无 'Tips'
- 脚本 `C:\Users\Admin\iconpark-render\verify11.mjs`：consoleAPICalled 只收 error/warning；`console.log("this.commentList: "+JSON.stringify(...))` 为 log 级不计入

## 根因分析

- 已确认的根因：`pages/comment/commentlist.vue:3` `:title="item.userId"`（服务端 Number）vs `uni_modules/uni-card/components/uni-card/uni-card.vue:61-64` `title: { type: String, default: '' }` → Vue2 dev prop 校验 warn 走 console.error
- 排除过的假设：网络/运行时异常（netfail/exception 均 []）；console.log JSON 串（log 级，不在收集范围）
- 问题归属：修改前已有（课程代码与组件 prop 声明不匹配）

## 最小修复

- 业务方已改：`pages/comment/commentlist.vue:3` → `:title="item.userId+''"`（课程 14work 完成分支原写法），仅显示层强转，渲染不变（截图 sha 不变）。
- 落盘方式备注：edit 工具遇文件锁 EIO，改用 .NET `WriteAllText` 写入成功（mtime 16:51:31）——IDE/工具锁可致「以为改了其实没落盘」。

## 验证记录

- [x] 复现：verify11 三个渲染轮 10/10/20 条 warn，计数与卡数×轮次吻合
- [x] 定位：file:line 对照（commentlist.vue:3 vs uni-card.vue:61-64）
- [x] 修复回归：verify11b 二跑（落盘后）13/13 true、errors []；toast 成功×2、10→刷新10→触底20、首卡 22/2024-04-28/新评论、无 Tips/footer、指示器停（内层 display:none 复合判据）、scrollW=clientW=450
- [x] 竞态对照：首跑（落盘前）12/13 且 40 warn，与二跑差异仅 errorsEmpty，证明红项唯一来源是该 prop warn

## 可复用规则

- 「console error/warning 全 []」类验收必须把 Vue warn 计入 error（Vue2 dev 经 console.error 发出）；命中 prop-type warn 先对照页面传值类型与组件 props 声明，决定修源头或显式白名单（记录原文+计数口径），不得静默忽略
- warn 条数＝卡数×渲染轮数，可反推触发轮次（10/10/20 ↔ onLoad/refresh/reach-bottom）
- 复跑验收前先核对磁盘源码 grep + 文件 mtime 与「宣称落盘时间」：取证窗口早于落盘会假红（watch 只编译磁盘内容）；edit 工具报 EIO/文件锁时改用可靠写入并回查 mtime，不以口头「已改」作为复跑前提

## 适用范围与不适用范围

- 适用：Vue2 dev 模式 prop 校验；uni-ui 同类 String prop 被传 Number 的场景；HBuilderX watch 工程的修复回归取证
- 不适用：Vue3（warn 发出通道不同，先实测）；production 构建（无 dev warn）

## 剩余风险

- 未发现已知剩余风险（修复回归绿）。若未来改回 Number 直传或升级 uni-card prop 声明，需重跑 verify11 口径。

## 关联

- 相关记录：[[踩坑-uni-appH5刷新指示器绝对定位隐藏与reload未重置pageIndex致分页取证误判]]
- 相关分类：03-通用/03-调试与验证
- 相关代码、命令或文档：`E:\fullstack-code\跨平台应用开发\wofule\pages\comment\commentlist.vue:3`；`uni_modules/uni-card/components/uni-card/uni-card.vue:60-64`；证据 `C:\Users\Admin\iconpark-render\verify11.mjs / verify11.json / verify11b.json / verify11-comment.png / verify11-after-refresh.png`