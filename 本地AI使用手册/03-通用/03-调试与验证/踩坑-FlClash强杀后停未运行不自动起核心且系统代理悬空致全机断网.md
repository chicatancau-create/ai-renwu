---
title: "FlClash 强杀后停「未运行」不自动起核心，系统代理悬空致全机断网"
date: 2026-11-11
domain: common
category: 调试与验证
status: verified
severity: high
stack: [FlClash, Windows, 系统代理]
tags: [代理, FlClash, 系统代理, 断网]
---

# 问题：FlClash 强杀后停「未运行」不自动起核心，系统代理悬空致全机断网

## 一句话结论

`taskkill /F` 结束 FlClash 再启动 exe，它会停在面板「未运行」**且不会自动拉起核心**；若系统代理仍指向它的端口，全机立刻断网。不要 taskkill FlClash；改规则靠 UI「停止/启动」或切订阅生效。

## 触发条件与影响

- 项目或功能：本机代理 FlClash（`D:\FlClash`，配置 `%APPDATA%\com.follow\clash`，端口 7890）。
- 环境与版本：Windows 11 28000，FlClash（Flutter + 自研 pipe 核心）。
- 触发条件：脚本/人 `taskkill /F /IM FlClash.exe /IM FlClashCore.exe` 后重新 `Start-Process FlClash.exe`。
- 影响范围：所有尊重系统代理的程序（浏览器/Qoder）全部失败。

## 复现步骤

1. 前置：FlClash 运行中、系统代理开 127.0.0.1:7890。
2. 操作：taskkill 两进程 → 重启 exe → 等 20–40s。
3. 预期：端口恢复监听。
4. 实际：进程在但 7890 不监听；面板状态「未运行」；`ProxyEnable=1` 仍指 7890 → 全机断网。

## 证据

- 重启后 `Get-NetTCPConnection -LocalPort 7890` 无 Listen；面板截图状态「未运行」。
- 在面板点蓝色「启动」后 7890 立即监听、走代理 200（实测 2026-11-11）。

## 根因分析

- 已确认：FlClash 的「运行」是 UI 状态，冷启动默认不运行核心；强杀丢失运行态，exe 重启不补。
- 排除：配置损坏（YAML 校验通过）、端口被占（无）。
- 归属：环境/应用行为，非本次代码引入。

## 最小修复

- 脚本/人都**不结束 FlClash**；只写配置文件。
- 新规则生效方式：UI 点一次「停止/启动」或切换一次订阅。
- 若已误杀：在面板点「启动」恢复；必要时先 `ProxyEnable=0` 保直连。

## 验证记录

- [x] 手动回归：点启动后 7890 监听、`curl -x 7890` 中转站/gstatic 200/204。
- [x] 脚本改为不杀 FlClash 后复跑 check，端口保持开放。

## 可复用规则

- 判代理「活着」要三件齐：主进程在 + 端口真 TCP 连上 + 面板「运行中」；只看进程或只看 `ProxyEnable` 都会误判。
- 任何「重启代理软件」的自动化，先确认它冷启动是否自动运行核心；FlClash 不会，故禁止 taskkill。

## 适用范围与不适用范围

- 适用：FlClash / 同类「运行态在 UI」的代理客户端。
- 不适用：Clash Verge 服务模式（内核由服务托管，行为不同，见关联记录）。

## 剩余风险

- 其它代理客户端冷启动行为各异，需逐个实测。

## 关联

- [[规则-代理软件关闭前必须先关系统代理]]
- [[踩坑-代理软件重启后不自动恢复系统代理开关唤醒须补开]]
- [[踩坑-App自更新后手动重装服务会装旧二进制且卸载器删内核致静默降级Sidecar]]
