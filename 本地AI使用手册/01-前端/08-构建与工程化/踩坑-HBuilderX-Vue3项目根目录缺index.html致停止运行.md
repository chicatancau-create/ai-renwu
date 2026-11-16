---
title: "HBuilderX Vue 3 项目根目录缺 index.html：编译前直接停止运行"
date: 2026-11-02
domain: frontend
category: "01-前端/08-构建与工程化"
status: verified
severity: medium
stack: ["HBuilderX 5.33", "uni-app", "Vue 3", "Vite"]
tags: ["HBuilderX", "uni-app", "Vue3", "index.html", "Vite", "构建入口"]
---

# 问题：Vue 3 项目编译时提示根目录缺少 index.html 并停止运行

## 一句话结论

HBuilderX 的 **Vue 3 / Vite** 工程要求项目根目录存在 `index.html`，且入口脚本指向 `/main.js`。
把 Vue 2 时代的“无 index.html”项目迁到 Vue 3 后，或清理临时构建文件时误删它，HBuilderX 会直接停止运行，不会进入页面编译。

## 触发条件与影响

- 项目：`E:\fullstack-code\跨平台应用开发`，uni-app + Vue 3
- 环境：HBuilderX `5.33.2026102115-alpha`，Windows
- 触发条件：`manifest.json` 已设 `"vueVersion": "3"`，但项目根目录没有 `index.html`
- 影响：HBuilderX 运行控制台报“请确认你的项目模板是否支持vue3：根目录缺少 index.html；已停止运行”，页面完全不启动

## 复现步骤

1. 前置：项目根目录只有 `App.vue`、`main.js`、`manifest.json`、`pages.json` 等，没有 `index.html`
2. 操作：HBuilderX 中执行“运行 → 运行到浏览器 → Chrome”
3. 预期：编译并打开 H5 页面
4. 实际：控制台提示根目录缺少 `index.html`，运行停止

## 证据

修复后 HBuilderX 日志：

```text
项目 跨平台应用开发 开始编译
编译器版本：5.33（vue3）
vite v5.2.8 dev server running at:
- Local: http://localhost:5173/
项目 跨平台应用开发 编译成功。
新生入学APP启动 at App.vue:4
```

浏览器实测：

- 首页、登录页正常渲染
- `uni-forms` 空值校验显示“请输入用户名 / 请输入密码”
- 输入 `student1 / 123456` 后显示“表单校验通过”
- 视口 390px 下 `body.scrollWidth = 390`，无横向溢出

## 根因分析

- 已确认根因：Vue 3 的 HBuilderX 工程使用 Vite，项目根目录必须有 HTML 入口；Vue 2 工程不需要这个文件。
- 排除的假设：
  - 不是 `manifest.json` 的 `vueVersion` 没改，已确认是 `"3"`
  - 不是组件未注册，补齐入口后 `uni-forms`、`uni-easyinput`、`uni-icons` 均正常
  - 不是端口冲突，HBuilderX 正常启动 Vite 5173
- 问题归属：迁移/清理时删除了 Vue 3 必需入口文件

## 最小修复

在项目根目录新增 `index.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
	<head>
		<meta charset="UTF-8" />
		<meta name="viewport" content="width=device-width, initial-scale=1.0" />
		<title>新生入学APP</title>
	</head>
	<body>
		<div id="app"></div>
		<script type="module" src="/main.js"></script>
	</body>
</html>
```

注意：HBuilderX 扁平工程的项目根就是 `main.js` 所在目录，入口写 `/main.js`，不要照搬 Vite CLI 模板写成 `/src/main.js`。

## 验证记录

- [x] 静态检查：`manifest.json`、`pages.json` JSON 解析通过
- [x] 类型检查或编译：HBuilderX 5.33 显示“编译成功”
- [x] 单元、集成或端到端测试：浏览器实测首页、登录页、表单校验
- [x] 构建：Vite 开发服务正常启动
- [x] 启动或手动回归：HBuilderX 实际运行通过

## 可复用规则

1. **Vue 3 迁移先查入口三件套**：`manifest.json` 的 `vueVersion=3`、`main.js` 的 `createSSRApp`、根目录 `index.html`。
2. **`index.html` 是源码入口，不是构建垃圾**：清理 `unpackage/`、`dist/`、`node_modules/` 时不要连带删除根目录 `index.html`。
3. **看到“根目录缺少 index.html”先补文件，不要先怀疑表单组件或路由**；Vue 2 项目没有这个文件是正常的，不能据此判断 Vue 3 也没问题。
4. **HBuilderX 与 Vite CLI 的目录假设不同**：HBuilderX 扁平工程入口是 `/main.js`；独立 Vite CLI 工程常是 `/src/main.js`，迁移时不要混用。

## 适用范围与不适用范围

- 适用：HBuilderX 运行的 uni-app Vue 3 / Vite 项目；从 Vue 2 迁移到 Vue 3 的工程
- 不适用：纯 Vue 2 工程、纯 Vite CLI 工程、非 HBuilderX 管理的项目

## 剩余风险

- HBuilderX 版本升级后入口约定可能变化；升级后先看运行日志中的 `编译器版本` 和 `Local` 地址。
- 本次只验证 H5，未验证原生 App 打包；原生平台入口要求需另行确认。

## 关联

- 相关记录：[[踩坑-HBuilder把容器目录当项目致报缺少pages.json且CLI传未导入路径假阴性]]
- 相关分类：[[01-前端/08-构建与工程化/README|构建与工程化]]
- 相关命令：HBuilderX `project open`、`launch web`、`logcat web`
