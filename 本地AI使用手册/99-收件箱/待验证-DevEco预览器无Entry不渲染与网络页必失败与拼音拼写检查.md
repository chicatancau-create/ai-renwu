---
title: "待验证：DevEco 预览器三种「看着像报错其实不是」的情况"
date: 2026-11-15
domain: frontend
category: 99-收件箱
status: needs-review
severity: low
stack: [HarmonyOS, ArkTS, DevEco Studio]
tags: [预览器, Entry, Preview, 网络API, 拼写检查, 误判]
---

# 待验证：预览器空画面、网络页永远失败、拼音资源名报「问题」

> 状态 `needs-review`：三种现象都亲眼在用户截图里出现过，但**没有做对照实验**（本机模拟器无系统镜像，无法自证），所以不升级为规则。

## 一句话结论

DevEco 预览器上最容易误判的三件事：① 打开的文件是 `@Component` 且没有 `@Entry`/`@Preview`，预览器就显示「没有可用的预览组件。通过装饰组件@Entry或@Preview来添加预览」——这不是错误，换一个入口文件即可；② 依赖 `@ohos.net.http` 的页面在预览器里**必然走失败分支**（预览器只模拟 UI，系统 API 支持有限），于是看到自己写的「连不上服务端」提示，误以为代码坏了；③ 底部「问题」面板里的 `拼写错误: 在单词 'shouye' 中` 是 IDE 词典在挑拼音资源名，与编译无关。

## 触发条件与影响

- 项目或功能：鸿蒙课程工程（首页/分类等 tab 子组件 + 网络取数页）
- 环境与版本：DevEco Studio 预览器 Phone (width: small, height: large)；`compatibleSdkVersion 6.1.1(24)`
- 触发条件：分别见上面三条
- 影响范围：容易被当成"页面报错/工程坏了"，实际是预览器能力边界与 IDE 检查项

## 证据（截图与实测）

```
# ① 面板原文
没有可用的预览组件。
通过装饰组件@Entry或@Preview来添加预览。
如何使用ArkUI预览？

# 该工程里带 @Entry 的文件（实测 grep）
pages/Index.ets  pages/me/Login.ets  pages/test/ContactPage.ets
pages/test/GridPage.ets  pages/test/ListPage.ets
→ 用户当时打开的是 pages/home/Index.ets（@Component export struct，无 @Entry）

# ② 预览器里网络页显示的是我们自己写的失败文案
连不上服务端（默认 http://127.0.0.1:3000）。请先启动 shopmall-api-v2-server…
# 同时本机实测：3000 端口无监听；用课件 .env 口令连 MySQL 返回 ER_ACCESS_DENIED_ERROR

# ③ IDE 问题面板
Index.ets  3 个问题
拼写错误: 在单词 'shouye' 中 :53
拼写错误: 在单词 'fenlei' 中 :57
# 同期命令行全量构建：BUILD SUCCESSFUL，ERROR 0
```

## 根因分析

- ①：预览器需要一个可渲染入口，`@Entry` 或 `@Preview` 是入口标记——**已确认**（面板文案 + 文件确实没有该装饰器）。
- ②：预览器不实现网络类系统 API——**未证实**，只是高置信度假设。反证条件：把服务端起起来、`BASE_URL` 指向可达地址，若预览器仍失败而真机成功，即可确认；本机因模拟器无镜像、MySQL 口令不通，**这条对照没做成**。
- ③：拼写检查独立于编译器——**已确认**（同一文件构建 0 错误）。

## 最小处置

- ①：切到带 `@Entry` 的文件再刷新预览；或给组件临时加 `@Preview`。
- ②：网络类页面用模拟器/真机验收；预览器里只验 UI 静态部分。别为了"预览器好看"往代码里塞假数据兜底。
- ③：把拼音词加进 IDE 字典即可；**不要改资源名**（一处改名要带动十几处 `$r('app.media.xxx')` 引用）。

## 验证记录

- [x] ①：文件装饰器与面板文案实测
- [ ] ②：待做「服务端可达 + 预览器 vs 真机」A/B
- [x] ③：同期构建日志 ERROR 0
- [ ] 单元/集成/端到端：无

## 可复用规则（暂定）

在预览器里看到"失败态文案"时，先分三层判：**是代码写的失败分支？→ 是环境问题（服务没起/口令不通）？→ 是预览器能力边界？** 三层各自有独立证据再下结论，不要把三层混成一句"页面报错"。

## 适用范围与不适用范围

- 适用：DevEco 预览器调试鸿蒙 UI/网络页
- 不适用：真机与模拟器行为；也不适用于 ArkTS 编译错误本身

## 剩余风险

②未经 A/B 证实，若预览器其实支持 http，则本记录的处置建议（必须上真机）会多余；届时应把该条降级为"仅环境未起"。

## 关联

- 相关记录：[[01-前端/06-网络请求与接口联调/HarmonyOS-网络图片不显示-缺INTERNET权限静默失败]]
- 相关分类：[[99-收件箱/收件箱]]
- 相关代码、命令或文档：`netstat -ano | grep :3000`；`hvigorw.js assembleHap --no-daemon`
