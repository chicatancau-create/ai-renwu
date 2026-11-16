---
title: "npm 报 404 时包名要用 debug log 确认，肉眼分不清 mysq12 与 mysql2"
date: 2026-11-15
domain: backend
category: 调试与验证
status: verified
severity: medium
stack: [npm, nodejs, registry]
tags: [npm, E404, registry.npmmirror, 调试取证]
---

# 问题：npm install 报 404，看着像源/网络问题，其实是包名打错一个字符

> `needs-review` 表示尚未完成验证；只有复现、定位、修复和验证都完成后，才改为 `verified`。本条已完成四步，状态 `verified`。

## 一句话结论

npm 的 404 报错里包名是被等宽字体糊住的（`mysq12` 的数字 1 与 `mysql2` 的字母 l 肉眼不可分），**唯一可靠判据是去读 `npm-cache\_logs\<时间戳>-debug-0.log` 里的 `http fetch GET 404 <url>` 那一行**；而且一条命令里只要有一个包 404，**整条 install 全部回滚**，同批能装的包也一个都不会落盘。

## 触发条件与影响

- 项目或功能：`E:\fullstack-code\Web\node`（Node 学习工程）装 express + mysql2。
- 环境与版本：本机 npm 全局 `registry=https://registry.npmmirror.com/`（见 `C:\Users\Admin\.npmrc`），无 proxy 配置。
- 触发条件：命令里把 `mysql2` 打成 `mysq12`。
- 影响范围：`express` 也没装上（当时目录里连 `node_modules` 都没有），而报错读起来像「镜像挂了/被墙」。

## 复现步骤

1. 前置条件：任意工程目录，本机 npm 全局 registry 为 npmmirror。
2. 操作或命令：`npm install express mysq12`（用错名）。**这条是用户 2026-11-04 的实际命令，本轮未重跑**；下面的源对照实验与修复验证才是本轮自产证据。
3. 预期结果：明确告知哪个包名不存在。
4. 实际结果：`npm error code E404 / 404 Not Found - GET https://registry.npmjs.org/mysq12`，且**报错里出现的是官方源 `registry.npmjs.org`**，与本机配置的 npmmirror 不一致，极易误判成源的问题。

## 证据

debug log 原文（`C:\Users\Admin\AppData\Local\npm-cache\_logs\2026-11-04T03_32_26_630Z-debug-0.log`）：

```
16 silly packumentCache full:https://registry.npmmirror.com/express cache-miss
17 http fetch GET 200 https://registry.npmmirror.com/express 256ms (cache miss)
20 silly packumentCache full:https://registry.npmmirror.com/mysq12 cache-miss
21 http fetch GET 404 https://registry.npmjs.org/mysq12 14159ms (cache skip)
```

同机实测对照（**2026-11-04 实测**，本记录 11-15 归档时订正日期）：

| 目标 | 结果 |
|---|---|
| `https://registry.npmjs.org/mysql2` 直连 | `http=200`（耗时 16.07s，慢但通） |
| `https://registry.npmjs.org/express` 直连 | `http=200` |
| 走 `127.0.0.1:7897` 代理取 `mysql2` | `http=200` |
| `https://registry.npmmirror.com/mysql2` | `http=200` |
| `https://registry.npmmirror.com/mysq12` | `http=404`，`redirect_url` 为空 |

## 根因分析

- 已确认的根因：包名字符打错（数字 `1` 当成字母 `l`）。npmmirror 与官方源对这个名字都回 404，对正确名字都回 200，说明与源、代理、DNS 无关。
- 排除过的假设：①「镜像被墙/源挂了」——被 200 对照否掉；②「npmmirror 缺这个包」——`mysql2` 在镜像上是 200；③「DNS 污染」——同机 `nslookup registry.npmjs.org` 确实超时，但 curl 直连能拿到 200，所以 DNS 超时不是本次 404 的原因（这条是**顺带观察**，不是本问题的根因）。
- **未证实**：配置是 npmmirror，log 第 20 行的 cache key 也是 npmmirror，但第 21 行实际发出去的请求打到了 `registry.npmjs.org`。npm 为何在这一步换源（回退重试？packument 的 `dist.tarball` 自带官方 URL？）本轮没有查证，只记现象。**不要据此写成规则。**
- 问题归属：本次修改引入（人工输入错误）。

## 最小修复

改命令即可，不涉及代码与配置：

```sh
npm install express mysql2
```

## 验证记录

- [x] 静态检查：`cat package.json` → `dependencies` 出现 `"express": "^4.22.3"`、`"mysql2": "^3.24.6"`
- [x] 安装结果：`added 102 packages in 19s`，`node_modules` 条目数 95
- [x] 运行时加载：`node -e "require('mysql2');require('express')"` → `mysql2 ok 3.24.6` / `express ok 4.22.3`
- [x] 手动回归：无（纯依赖安装）
- [ ] 类型检查 / 构建：不适用

## 可复用规则

下次遇到 npm E404，**先读 debug log 的 `http fetch GET 404` 行确认原始包名**，再判断是不是源的问题；报错里显示的域名与 `npm config get registry` 不一致时，**不构成「源配错」的证据**。

顺带：同一条 `npm install a b c` 里任何一个包 404，其余包全部不装。别看到「express 已在 package.json 里」就以为它装好了——用 `ls node_modules` 实测。

## 适用范围与不适用范围

- 适用：本机所有 npm/pnpm 安装失败排查；等宽终端里的 `l/I/1/0/o` 类字符混淆。
- 不适用：`EACCES`、`ENOTFOUND`、`ECONNRESET` 这类非 404 失败；私有 registry 的权限型 404（报错文案相同，需另判）。

## 剩余风险

npmmirror 与官方源对同一个错名都回 404，但 npm 在两者之间的重试逻辑未查清；若将来出现「包名正确却仍 404」，本条结论不足以覆盖，需单独取证。

## 关联

- 相关记录：`踩坑-钉死内核同名包版本遇宿主自更新即降级致启动fatal.md`（同为「依赖解析失败但报错指向别处」）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关命令：`npm config get registry`、`cat %LOCALAPPDATA%\npm-cache\_logs\*-debug-0.log`
