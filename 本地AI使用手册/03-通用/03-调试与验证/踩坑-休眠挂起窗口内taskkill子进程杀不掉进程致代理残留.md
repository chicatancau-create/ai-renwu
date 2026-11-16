---
title: "休眠挂起窗口内 taskkill /F 子进程杀不掉进程，致代理软件残留"
date: 2026-11-12
domain: common
category: 调试与验证
status: verified
severity: high
stack: [Python, Windows, Win32, 休眠]
tags: [休眠, PBT_APMSUSPEND, taskkill, TerminateProcess, 子进程, 代理, 收尾]
---

# 问题：休眠挂起窗口内 taskkill /F 子进程杀不掉进程，致代理软件残留

## 一句话结论

在"系统即将休眠/关机"的收尾窗口里终止进程，别起 `taskkill /F` 子进程——它在挂起窗口内可能起不来/超时且静默失败；改用进程内 `OpenProcess+TerminateProcess` 直调。

## 触发条件与影响

- 项目或功能：`G:\AIrenwu\01_任务归档\2026-10-10_桌面核心脚本\03_工具脚本\session_end.py`（SessionEndGuard：关机/休眠收尾退代理软件）
- 环境与版本：Python 3.14；Win11；FlClash（`D:\FlClash\FlClash.exe` + `FlClashCore.exe`）
- 触发条件：真实过夜休眠，`PBT_APMSUSPEND` 处理途中系统即将冻结；温和 `taskkill /IM`（WM_CLOSE）对托盘应用无效，落到强制档 `taskkill /F`。
- 影响范围：代理软件没被退出、跨休眠残留；叠加"唤醒补开代理"缺失，用户唤醒后网络状态错乱。

## 复现步骤

1. 前置条件：FlClash 在跑，系统代理开。
2. 操作或命令：真实过夜休眠（11-11 夜 → 11-12 晨）。
3. 预期结果：收尾把 FlClash / FlClashCore 退出。
4. 实际结果：日志记「仍有残留 [46244]」，FlClash 原样活到早上。

## 证据

- `02_证据日志\watch.log` 昨夜：`会话守卫[休眠]：FlClash.exe 仍有残留 [46244]`，该进程次日仍在。
- 修复后真机受控验证（`tmp\_verify_kill_resume.py`）：FlClash 46244 + FlClashCore 15256 均被终止。

## 根因分析

- 已确认的根因：强制档用 `taskkill /F /IM` 子进程。休眠挂起窗口内起子进程不可靠（起不来/超时），失败是静默的，进程没被杀死。
- 排除过的假设：不是"FlClash 拒绝退出"——进程内 TerminateProcess 对同一进程可杀（非提权进程）。
- 问题归属：修改前已有（旧实现一直用 taskkill /F）。
- 注：具体是"起不来"还是"超时"未单独取证；进程内直调绕开了子进程这一整层，真机验证有效。

## 最小修复

`_exit_apps` 强制档改用注入的 `kill_pid`（watch.py 的 `_kill_pid`：OpenProcess+TerminateProcess 进程内直调），不起子进程；未注入时才兜底 `taskkill /F`。`kill_pid` 返回 `(ok, reason)`，失败记原因。

## 验证记录

- [x] 编译：`py_compile session_end.py` OK
- [x] 单元：`test_session_end_resolve_20261111.py` [H] 5 断言（强制走 kill_pid、无 taskkill /F、失败记原因）PASS
- [x] 真机受控：`_verify_kill_resume.py` 杀掉 FlClash + core PASS
- [ ] 真实过夜休眠（新代码）：尚未自然触发，待今晚以日志复核

## 可复用规则

在 `WM_QUERYENDSESSION` / `PBT_APMSUSPEND` 这类"系统即将挂起"的收尾窗口里做进程清理，用进程内 Win32 API（OpenProcess+TerminateProcess）直调，不要起 taskkill/sc/subprocess 子进程——子进程可能起不来或超时，且失败静默。正常运行时的进程管理不受此限。

## 适用范围与不适用范围

- 适用：关机/休眠收尾里的进程终止。
- 不适用：正常运行时的进程管理（子进程没问题）；提权进程（TerminateProcess 需相应权限，本例 FlClash 非提权）。

## 剩余风险

新代码未经历真实过夜休眠（受控验证在正常运行时做的）；对提权进程需另论权限。

## 关联

- 相关记录：[[规则-代理软件关闭前必须先关系统代理]]、[[踩坑-休眠冻结收尾致唤醒广播丢失须主动补唤醒]]、[[踩坑-代理软件重启后不自动恢复系统代理开关唤醒须补开]]
- 相关代码：`03_工具脚本\session_end.py` `_exit_apps`；`03_工具脚本\watch.py` `_kill_pid`
