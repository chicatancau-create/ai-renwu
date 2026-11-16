---
title: "AI 面板「连接失败 耗时 1ms」是没填密钥，不是网络不通"
date: 2026-10-12
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: low
stack: [Electron, Gemini API, 网络诊断]
tags: [调试, 网络, AI接入, Windows]
---

# 问题：桌面客户端的 AI 主题设置点「测试连接」立刻失败，报 `GEMINI_API_KEY is not configured in settings`

## 一句话结论

**耗时 1ms 就是证据** —— 一次真实的 HTTPS 往返不可能只用 1 毫秒，这条报错来自发请求之前的本地校验。
先按「有没有发请求」分流，再决定去查网络还是查表单。

## 触发条件与影响

- 项目或功能：`D:\folia-major`（Electron 音乐客户端）设置 → AI 主题设置 → 测试连接。
- 环境与版本：Win11 28000；系统代理 `127.0.0.1:7897`（`ProxyEnable=1`）；「为AI使用系统代理」已开。
- 触发条件：密钥输入框留空（占位符 `AI Theme Generation Key` 容易被当成"已经填过了"）。
- 影响范围：只是这个功能不可用；同时会误导人去折腾梯子。

## 复现步骤

1. 前置条件：AI 供应商选 Google Gemini，密钥框不填。
2. 操作或命令：点「测试连接」。
3. 预期结果：报"未配置密钥"。
4. 实际结果：`连接失败 / 耗时: 1 ms / GEMINI_API_KEY is not configured in settings`。

## 证据

- 代码侧（`electron/aiTextClient.cjs`）：`runGeminiCompletion()` 在 `customFetch(...)` **之前**
  就 `if (!apiKey) throw new Error('GEMINI_API_KEY is not configured in settings')`（:580-583），
  测试连接的兜底分支同样直接回这句（:782）。也就是说这条文案**只可能来自本地校验**。
- 网络侧实测（Python urllib，同一端点）：
  - 走 `127.0.0.1:7897` → **HTTP 403，0.8 s**
  - 完全直连（空 ProxyHandler）→ **HTTP 403，0.9 s**
  - 正文 `{"error":{"code":403,"message":"Method doesn't allow unregistered callers (callers without established identity)..."}}`
  → `generativelanguage.googleapis.com` 在本机**直连就通**，TLS 与 DNS 都正常，缺的只是鉴权。
  这与「`www.google.com` 被路由器 DNS 污染成 Facebook 段」不矛盾：**污染是按域名的，不能从主站被污染推出 API 域名也不可达**。
- 该客户端调的是固定端点 `.../v1beta/models/gemini-3-flash-preview:generateContent`，
  密钥放 **`x-goog-api-key` 请求头**（不是 `?key=`），Gemini 分支不给模型/地址输入框（`apiUrl`、`model` 只在「其他兼容接口」下读取）。

## 根因分析

- 已确认的根因：表单值为空 → 本地校验抛错，请求从未发出。
- 排除过的假设：不是代理没生效（直连都能拿到 Google 的 403 JSON）；不是端点被墙；不是模型名写错（模型名写死，且请求没走到那一步）。
- 问题归属：使用侧输入缺失，非程序缺陷。

## 最小修复

到 `https://aistudio.google.com/apikey` 取一把 **AI Studio API key**（`AIza` 开头）粘进输入框 → 点「保存」→ 再测。
注意「测试连接」读的是**表单当前值**（不保存也能测），但真正生成主题读的是**已保存**的值，所以必须保存一次。
密钥在 Windows 下由 Electron safeStorage(DPAPI) 封成 `GEMINI_API_KEY_SEALED` 再落 config.json，不明文存储。
不想用 Google 就切「其他兼容接口」填中转的 `chat/completions` 基址 + 模型名 + key（非官方 OpenAI 端点不会收到 `response_format: json_schema`，走 `json_object` + 调用方自校验）。

## 验证记录

- [x] 代码定位：抛错点在 fetch 之前（文件行号见证据）。
- [x] 网络对照实验：同一端点走代理 / 直连各测一次，均 403 且耗时 <1 s。
- [x] 系统代理状态读取：`ProxyEnable=1`、`ProxyServer=127.0.0.1:7897`。
- [ ] 端到端：未做（需要真实 API key，本机 `.gkeys` 里没有 Gemini key，vault 内 4 把都是 53 字符，与 39 字符的 Google API key 不符）。

## 可复用规则

**看到「失败 + 耗时个位数毫秒」，先判定"根本没发请求"**：抓包/看日志确认无出站请求 → 去读代码里 fetch 之前的校验分支；
只有耗时到了几百毫秒以上才值得怀疑网络与代理。
判断某个 API 域名在本机是否可达，用**不带凭据**打同一个端点：拿到 `401/403` 的 JSON 错误体即证明 DNS+TLS+服务端链路全通，
比 ping 主站有意义。

## 适用范围与不适用范围

- 适用：任何"设置面板里填 key + 点测试连接"的桌面/Web 客户端排障；本机对 Google 系 API 域名的可达性判断。
- 不适用：报错耗时几百毫秒以上（那才是网络层）；报错文案来自远端 4xx/5xx 响应体的情况。

## 剩余风险

本机 4 个 Google 账号卡在 Code Assist 后端的 `VALIDATION_REQUIRED`（手机扫码），**AI Studio 建 key 是否同样被拦未证实**；
另按 Google 2026-08-18 官方口径，AI Pro/Ultra 权益**不落** API key，key 只有 Free/Tier 1-3 档，别指望 Pro 带来高配额。

## 关联

- 相关记录：[[03-通用/03-调试与验证/踩坑-虚拟网卡空metric抢走默认路由致域名假超时|虚拟网卡空 metric 抢走默认路由致域名假超时]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：`D:\folia-major\electron\aiTextClient.cjs:579-617`、`D:\folia-major\electron\aiCredentialStore.cjs:1-28`
