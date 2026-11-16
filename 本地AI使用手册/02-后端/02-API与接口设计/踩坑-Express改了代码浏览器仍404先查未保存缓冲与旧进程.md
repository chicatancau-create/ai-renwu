---
title: "Express 改了代码浏览器仍 404：先查编辑器是否保存、端口上跑的是不是旧进程"
date: 2026-11-15
domain: backend
category: "API 与接口设计"
status: verified
severity: medium
stack: [Node.js 24, Express 4, VS Code 终端]
tags: [404, Cannot GET, 未保存缓冲, 无热重载, 旧进程占端口, EADDRINUSE]
---

# 问题：代码里明明写了路由，浏览器打开却 404 `Cannot GET /`

> `verified`：现象、根因、修复与验证都在本轮实际执行过。

## 一句话结论

两件事叠在一起：① 新加的 `app.get('/')` 只存在编辑器缓冲里、没落盘；② 端口上跑着更早启动的旧 Node 进程。Node 没有热更新，进程只在启动时读一次代码，所以"改了不生效"必须回到两个问题：**磁盘里是什么**、**是谁在跑**。

## 触发条件与影响

- 项目或功能：Express 路由练习（仓库 `Web/node/app.js`）
- 环境与版本：Windows 10.0.28000；Node v24.15.0（复现时）/ v24.22.1（后续会话）；Express 4.x；VS Code 集成终端（PowerShell）
- 触发条件：编辑器里新增路由后没有 Ctrl+S；同时服务是更早启动的
- 影响范围：仅本地开发。表现为"代码看起来完全正确却 404"，容易误判成路由写法、中间件顺序或 Express 配置问题

## 复现步骤

1. 前置条件：`app.js` 只有 `app.listen(3000)`，先 `node app` 启动
2. 在编辑器里加 `app.get('/', (req,res)=>{res.send("服务器运行正常")})`，**不保存**
3. 浏览器访问 `http://localhost:3000/` → 打不开 / 报错
4. `curl` 直连拿真实响应体 → `HTTP/1.1 404 Not Found` + `Cannot GET /`；再读磁盘文件，里面确实没有该路由

## 证据

- `curl -s --noproxy '*' -i http://127.0.0.1:3000/` → `HTTP/1.1 404 Not Found`、`X-Powered-By: Express`、body `<pre>Cannot GET /</pre>`
- `Get-CimInstance Win32_Process -Filter "Name='node.exe'"` → `ProcessId 51184 / CommandLine "D:\Node.js\node.exe" app / CreationDate 2026-11-11 8:44:03`，父进程是 VS Code 终端 shell
- 保存 + 重启后同一请求 → `HTTP/1.1 200 OK`，body `服务器运行正常`；`/api/products/list` → `[{"id":1,"name":"苹果"},{"id":2,"name":"wofule"}]`，`Content-Type: application/json; charset=utf-8`
- 另起第二个实例 → `Error: listen EADDRINUSE: address already in use :::3000`（反证端口上确实有进程在跑）
- 附带：`Get-NetTCPConnection -LocalPort 3000 -State Listen` 在本机回空，去掉 `-State` 才有 Listening 行（本机已知坑，见关联记录）

## 根因分析

- 已确认的根因：① 编辑器未保存，磁盘文件没有路由；② 运行中的进程是更早启动的旧代码，Node 不热重载
- 排除过的假设：系统代理（`ProxyOverride` 含 `localhost;127.*`，且 `--noproxy` 直连同样 404）；端口被别的服务占用（响应体是 Express 自己的 `Cannot GET /`，说明服务确实是自己的，只是代码旧）
- 问题归属：环境与时序（编辑器未保存 + 长跑进程），不是代码写法错误

## 最小修复

Ctrl+S 保存 → 终端 Ctrl+C → 重新 `node app`。要免手重启用 `npx nodemon app.js`。

## 验证记录

- [x] 启动：`node app` 打印 `Server is running on port 3000`
- [x] 手动回归：`curl` 两个路由分别返回 200「服务器运行正常」与 200 JSON
- [ ] 单元 / 集成测试：课程样例无测试，未执行
- [ ] 构建：无构建步骤

## 可复用规则

1. 浏览器结果不对，先 `curl <url> -i` 直连拿真实状态码和响应体，不要用浏览器页面当证据（细节会被吞，代理和缓存还会伪装）。
2. 拿到 `OwningProcess` 后用 `Get-CimInstance Win32_Process` 看 **CommandLine + CreationDate**；CreationDate 早于文件 mtime ⇒ 跑的是旧代码。
3. 编辑器缓冲 ≠ 磁盘：先看标签页的未保存圆点，或 `git diff -- <文件>` 是否为空。
4. 本机判端口死活不要用 `-State Listen` 过滤（恒回空）。
5. 解释器型服务改代码一律重启；"改完刷新就生效"只在带文件监听的前端 dev server / nodemon / pm2 watch 下成立。

## 适用范围与不适用范围

- 适用：任何解释器型本地服务（Node / Python / Go）"改了不生效"的排查
- 不适用：有文件监听的运行器（nodemon、vite、uvicorn --reload）会自动重启，CreationDate 会随之变化，此时应查监听器本身

## 剩余风险

- nodemon 在本机未安装、未实测。
- 若端口被其他用户或其他服务占用，`Stop-Process` 可能受权限限制（本次进程属当前用户，未遇到）。

## 关联

- 相关记录：[[02-后端/01-架构与项目结构/踩坑-CommonJS目录下js顶层await报SyntaxError]]、[[03-通用/03-调试与验证/踩坑-杀软断网修复清零系统代理且StateListen过滤假报端口死]]
- 相关分类：[[02-后端/02-API与接口设计/README|API 与接口设计]]
- 相关代码：仓库 `E:\fullstack-code\Web\node\app.js`
