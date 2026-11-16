---
title: "会话进行中装插件会让内核热重载，当前 turn 报 sessionController unavailable"
date: 2026-11-03
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [DeepSeek Harness, Electron, pnpm, 插件profile]
tags: [时序竞争, 热重载, 安装不等于配置]
---

# 问题：DSH 里一个跑了 44 分钟的 turn 突然 `typert gateway: session/prompt: active Service "sessionController" is unavailable (gateway/service-unavailable)` + `Connection error`

## 一句话结论

同一分钟插件管理器正在改写该 profile 的 `package.json` / `node_modules`，**内核热重载插件时会话控制器短暂不可用**，长 turn 的 5 次重试全撞上这个窗口；内核没崩、安装也成功了——丢的只是那一轮。另一条同样重要：**装好包 ≠ 配好功能**，`cordis.patch.yml` 没写预设的话，重启也看不到新预设。

## 触发条件与影响

- 项目或功能：给 DSH 的 `desktop` profile 安装 bundle（`plugin_manager.install_bundle` → pnpm）
- 环境与版本：DeepSeek Harness 桌面端；profile 目录 `~\.dsh\profiles\desktop`；pnpm v11.28.5
- 触发条件：**同一个内核进程正在跑长 turn 时**执行安装
- 影响：当前 turn 失败（可重发）；不会损坏 profile

## 复现步骤

1. 前置条件：某会话正在执行一个长时间 turn（本例「深度求索中，用时 44 分 20 秒」）
2. 操作：另一处触发 `install_bundle`，pnpm 改写 profile 的 `package.json` 与 `node_modules`
3. 预期：安装完成，会话继续
4. 实际：会话端 `已重试模型请求 (1/5) 1s … (5/5) 8s` 后 `本轮运行失败 Connection error`，顶部弹 `gateway/service-unavailable`

## 证据（本轮实测，四条互证）

```
DSH 进程创建时间：5 个进程全部 11-03 12:55:04~05  ← 报错在 15:55，内核没重启也没崩
pnpm.log（operation-3lmXh1）：+ dsh-super-agent 0.0.5 / Done in 5s   ← 安装成功
package.json：bundles 已含 "dsh-super-agent"，dependencies 已写 "dsh-super-agent": "0.0.5"
node_modules\dsh-super-agent\package.json：version 0.0.5, main lib/index.js, 带 dsh manifest
文件 mtime：package.json 与 node_modules 均为 11-03 15:55  ← 与报错同一分钟
```

排除过的假设：内核崩溃（进程存活且创建时间未变）；安装失败（pnpm 日志与落盘文件都成功）；
网络/模型线路故障（重试 5 次都失败但 15:55 之后会话可继续，且失败信息是**服务不可用**而非超时）。

## 根因分析

- 已确认的根因：安装动作改写 profile 文件 ⇒ 内核热重载插件 ⇒ 内部 gateway 的 `sessionController` 服务在重载窗口内不可用；正在飞行中的 `session/prompt` 直接失败。
- 次生发现（更容易被忽略）：`cordis.patch.yml` mtime 仍是 **11-01 16:32**，内容里 `super-agent` 出现 0 次、
  `solo/team/research/optimization` 四个预设各 0 次 ⇒ **只装了包、没写配置**。
  此时即便重启内核，功能也不会出现，容易被误判成「装失败了」。
- 问题归属：操作时序（本次会话内同时做「装插件」和「跑长 turn」）。

## 最小修复 / 正确顺序

1. **别在会话跑到一半时装/卸插件**。要装就等当前 turn 结束，或先让会话停下来。
2. 装完先做**两件事再判断成败**：① 看 `pnpm.log` 与 `node_modules/<pkg>/package.json` 证「装上了」；
   ② 看 `cordis.patch.yml` 是否写入了该插件的预设/host 行，证「配好了」。
3. 新 bundle **必须重启内核才会加载**（热重载只覆盖配置类改动，不足以装载新插件）。
4. 验收三条：预设列表出现预期条目、插件的 host 服务激活、启动日志无加载报错。

## 验证记录

- [x] 进程存活 + 创建时间未变 ⇒ 排除崩溃
- [x] pnpm 日志 + 落盘文件 + package.json 三处一致 ⇒ 安装成功
- [x] `cordis.patch.yml` mtime 与内容 grep ⇒ 证实「未配置」
- [x] 报错时刻与写盘时刻同分钟 ⇒ 时序竞争成立
- [ ] 重启内核后预设是否出现：**未做**（留给下一轮）

## 可复用规则

- 看到 `active Service "<x>" is unavailable (gateway/service-unavailable)` 这类**服务级不可用**报错，
  先查「同一分钟有没有东西在改它的配置/依赖目录」，再怀疑网络。
- 判「装插件有没有成功」要分三层：**下载解包 / 清单登记 / 配置生效**，任一层缺失都会表现为「装了但没用」。

## 适用范围与不适用范围

- 适用：DSH 及任何「插件装进 profile + 内核热重载」的桌面 Agent 运行时
- 不适用：纯静态库安装（无运行中内核监听 profile 目录）

## 剩余风险

- 热重载窗口的确切时长未量到（只知道 5 次重试、约 8 秒内都没恢复）；若重试预算更长是否能自愈，未证实。
- 未验证「重启后四个预设是否真的出现」，因此不能排除 `dsh-super-agent 0.0.5` 与内核 0.2.1 存在接口不匹配。

## 关联

- 相关记录：[[踩坑-执行环境Start-Process子进程在工具会话结束时被连带回收]]、[[踩坑-API密钥报无效实为请求形态不对-OpenAI兼容网关]]（同为「报错文案把归因带偏」）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
