---
title: "CommonJS 目录下的 .js 写顶层 await 必报 SyntaxError"
date: 2026-11-15
domain: backend
category: "架构与项目结构"
status: verified
severity: low
stack: [Node.js 24, CommonJS, ESM]
tags: [SyntaxError, 顶层await, package.json type, require]
---

# 问题：`node xxx.js` 报 `await is only valid in async functions and the top level bodies of modules`

> `verified`：报错、根因、最小修复与运行验证均已实测。

## 一句话结论

最近的 `package.json` 写了 `"type": "commonjs"`，该目录所有 `.js` 都按 CommonJS 解析，而 CommonJS 模块顶层不允许 `await`（只有 ES Module 顶层才允许）。同目录其他练习文件都在用 `require(...)`，不能整体改成 `"type": "module"`，最小解法是把顶层 `await` 包进 async 函数。

## 触发条件与影响

- 项目或功能：`fs/promises` 练习脚本（仓库 `Web/node/molu.js`）
- 环境与版本：Windows；Node v24.15.0；同目录 `package.json` 为 `"type": "commonjs"`
- 触发条件：在模块顶层直接写 `await fsp.readdir(...)`
- 影响范围：脚本一行都执行不了，退出码 1

## 复现步骤

1. 前置条件：目录下有 `package.json` 且 `"type": "commonjs"`；脚本内用 `require("fs")`
2. 顶层写 `await fsp.mkdir("./uploads/avatars/2025", { recursive: true })`
3. `node molu.js`
4. 实际结果：`SyntaxError: await is only valid in async functions and the top level bodies of modules`

## 证据

- 报错栈：`at wrapSafe (node:internal/modules/cjs/loader:1763:18)` → `at Module._compile` → `at Module.load`，说明文件被当作 CommonJS 编译
- `Web/node/package.json:14` 为 `"type": "commonjs"`
- 把整段包进 `(async () => { ... })();` 后重新执行：退出码 0，输出依次正常

## 根因分析

- 已确认的根因：`"type": "commonjs"` 决定 `.js` 使用 CommonJS；CommonJS 模块顶层不是 async 上下文，语法层面直接拒绝 `await`
- 排除过的假设：Node 版本太旧（v24 支持 ESM 顶层 await）；文件编码 / BOM（报的是明确语法错误，不是乱码）
- 问题归属：工程配置

## 最小修复

整段包进 `(async () => { ... })();`，`require` 原样保留，改动最小。

另外两条路：
1. 改名 `.mjs` —— 必须同时把 `require` 换成 `import`，只改名会报 `require is not defined`
2. `package.json` 改 `"type": "module"` —— 本目录其他文件都写 `require(...)`，会全部坏掉，不要这么改

## 验证记录

- [x] 执行：修改后 `node molu.js` 退出码 0
- [x] 手动回归：输出 `[ 'a.txt', 'avatars' ]`、`true` / `false` / `9`（字节数）、`文件存在`、`[ 'src\\hello.txt' ]`
- [ ] 单元 / 集成测试：练习脚本无测试
- [ ] 构建：无

## 可复用规则

1. 见到 `await is only valid in async functions and the top level bodies of modules`，先查**最近一层 `package.json` 的 `type`**，再看文件扩展名（`.js` / `.cjs` / `.mjs`）。
2. 单文件要 ESM 时走 `.mjs`，并同时把 `require` 改 `import`；两件事少一件都会换一种错。
3. 目录级切换模块系统前，先 `grep -rl "require(" <目录>` 数一遍受影响文件。

## 适用范围与不适用范围

- 适用：Node 下 `.js/.cjs/.mjs` 混用的练习与小项目
- 不适用：由打包器（webpack / vite）接管模块语义的工程，其规则由 loader 决定

## 剩余风险

- 未实测把本目录改成 `"type": "module"` 后具体坏掉多少个文件（只做了静态判断，且已明确不采用该方案）。

## 关联

- 相关记录：[[02-后端/02-API与接口设计/踩坑-Express改了代码浏览器仍404先查未保存缓冲与旧进程]]
- 相关分类：[[02-后端/01-架构与项目结构/README|架构与项目结构]]
- 相关代码：仓库 `E:\fullstack-code\Web\node\molu.js`
