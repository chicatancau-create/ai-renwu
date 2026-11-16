---
title: "关机被取消（WM_ENDSESSION wParam=FALSE）须还原已做的破坏性收尾"
date: 2026-11-12
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Python, Windows, Win32, 关机]
tags: [WM_QUERYENDSESSION, WM_ENDSESSION, 关机取消, 收尾, 还原, 系统代理]
---

# 问题：关机被取消（WM_ENDSESSION wParam=FALSE）须还原已做的破坏性收尾

## 一句话结论

在 `WM_QUERYENDSESSION` 就做破坏性收尾（杀进程/关代理）时，必须处理 `WM_ENDSESSION(wParam=FALSE)`——关机可能被别的程序否决，会话没结束，已做的破坏要能还原；只复位标志不够。

## 触发条件与影响

- 项目或功能：`session_end.py` 关机/注销收尾
- 环境与版本：Python 3.14；Win11；FlClash
- 触发条件：收尾在 `WM_QUERYENDSESSION` 执行（关代理 + 退应用）后，另一程序否决关机，Windows 发 `WM_ENDSESSION(wParam=FALSE)`。
- 影响范围：用户回到桌面，FlClash 被杀、代理被关，但会话并没结束——一个没代理的桌面。

## 复现步骤

1. 前置条件：FlClash 在跑、代理开。
2. 操作或命令：触发关机/注销 → 收尾执行 → 另一程序取消关机（`WM_ENDSESSION wParam=FALSE`）。
3. 预期结果：会话未结束，应用与代理恢复原状。
4. 实际结果（旧实现）：只复位标志，FlClash 没起、代理没开。

## 证据

- 逻辑证据：`WM_QUERYENDSESSION` 分支先关代理 + 退应用；`WM_ENDSESSION(FALSE)` 旧分支只复位 `handled_shutdown`/`handled_resume`。
- 回归：test [K] 8 断言模拟完整消息序列（QUERYENDSESSION → ENDSESSION(FALSE)）。

## 根因分析

- 已确认的根因：收尾提前到 `WM_QUERYENDSESSION`（为在进程被杀前完成），但没考虑"关机可能被取消"；`WM_ENDSESSION(FALSE)` 分支没还原已做的破坏性收尾。
- 问题归属：修改前已有。

## 最小修复

`WM_ENDSESSION(FALSE)` 分支：先 `tore_down=handled_shutdown`，再复位两标志，若 `tore_down` 调 `_restart_apps()`（重启应用 + 补开代理）。`_restart_apps` 不检查 `restart_on_resume`——取消恢复必须无条件还原误拆，不受"唤醒是否自动重启"偏好限制。

## 验证记录

- [x] 编译 OK
- [x] 单元：[K] 8 断言（收尾记下补开/取消后拉起应用/取消后补开代理/有恢复日志/handled复位/没收尾就取消不恢复/关掉自动重启偏好仍恢复）PASS，全套 57/57
- [ ] 真实"关机被取消"场景：未在本机复现（需另一程序否决关机），逻辑已用消息序列回归覆盖

## 可复用规则

在 `WM_QUERYENDSESSION` 做破坏性收尾（杀进程/关代理/停服务）时，必须处理 `WM_ENDSESSION(wParam=FALSE)`：关机可能被取消，已做的破坏要能还原。还原逻辑不应受"正常唤醒是否自动重启"这类偏好开关限制——误拆必须无条件还原。

## 适用范围与不适用范围

- 适用：任何在 `WM_QUERYENDSESSION` 提前做破坏性收尾的自动化。
- 不适用：收尾只在 `WM_ENDSESSION(TRUE)` 才做的实现（那时会话真要结束，无需还原）。

## 剩余风险

真实"关机被取消"未在本机复现，逻辑由消息序列回归覆盖。

## 关联

- 相关记录：[[规则-代理软件关闭前必须先关系统代理]]、[[踩坑-测试触发真实收尾动作关掉系统代理]]（测这个分支时务必打桩，别真关代理）、[[踩坑-代理软件重启后不自动恢复系统代理开关唤醒须补开]]
- 相关代码：`session_end.py` `_on_message` WM_ENDSESSION 分支 / `_restart_apps`
