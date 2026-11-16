---
title: "ctypes 窗口过程在 CreateWindowExW 内同步回调，字段未初始化致静默 NULL"
date: 2026-11-11
domain: common
category: 04-工程规范与安全
status: verified
severity: high
stack: [Python, ctypes, Win32]
tags: [WndProc, CreateWindowExW, 托盘, 静默失败]
---

# 问题：ctypes 窗口过程在 CreateWindowExW 内同步回调，字段未初始化致静默 NULL

> 2026-11-15 回写。事件发生在 2026-11-11 的 cc-hud 托盘改造（G:\cc-hud\cchud_next\tray.py）。

## 一句话结论

`CreateWindowExW` 会在调用内部**同步**派发 `WM_NCCREATE`/`WM_CREATE` 给 WNDPROC；若回调里访问了尚未赋值的实例字段，Python 抛异常 → 回调返回 0 → `CreateWindowExW` 返回 NULL 且 `GetLastError()==0`，表现为「窗口/托盘建不出来」却没有任何错误码。

## 触发条件与影响

- 项目或功能：用 ctypes 注册 WNDCLASS + WNDPROC 创建隐藏窗口（托盘宿主窗、消息窗等）。
- 环境与版本：Windows 11 26x00、CPython 3.14 x64、ctypes。
- 触发条件：`self.hwnd = u.CreateWindowExW(...)` 写在 `self._last = {}`、`self.added = False` 等字段初始化**之前**，而 WNDPROC 分支里读了这些字段。
- 影响范围：托盘注册整条链路静默失败；上层只看到「hwnd 为 0 / WinError 0」，极易误判成 Shell 问题或权限问题。

## 复现步骤

1. 前置条件：WNDPROC 的 `WM_NCCREATE`/`WM_CREATE` 分支引用 `self._taskbar_created` 等字段。
2. 操作或命令：先 `CreateWindowExW` 再初始化字段（旧代码顺序）。
3. 预期结果：窗口创建成功或给出明确错误码。
4. 实际结果：`CreateWindowExW` 返回 NULL，`ctypes.WinError()` 报 `[WinError 0]`；基线版本同样复现（说明不是新引入）。

## 证据

- 旧顺序下 `self.hwnd == 0`、`GetLastError() == 0`；把字段初始化移到 `CreateWindowExW` 之前后一次创建成功。
- 修复后实测：`runtime.json` 中 `tray_added: true`、`tray_getrect_rc: 0`、`tray_rect` 非空；`tools/tray_click.py` 与最终验收 18/18 通过（2026-11-11 17:21 的 artifacts）。
- 同族坑（一并修）：x64 下 `RegisterClassExW` 未设 `argtypes/restype`、`hInstance` 以裸 int 传入会被按 32 位截断 → 同样静默 NULL；改 `ctypes.c_void_p(hinst)` + 显式 `argtypes` 后稳定。

## 根因分析

- 已确认的根因：Win32 创建窗口是同步回调模型；ctypes 回调里的 Python 异常被吞成返回值 0，创建函数据此返回 NULL 且不设 last-error。
- 排除过的假设：不是类名冲突（失败路径已 `DestroyWindow` 清理）；不是 Shell 丢弃图标（那发生在 NIM_ADD 之后，而此处窗口都没建出来）。
- 问题归属：修改前已有（基线同病），本次修复。

## 最小修复

1. 所有 WNDPROC 会读到的字段（含 `_last`、`added`、`_icons`、`_tip`、`_taskbar_created`）在 `CreateWindowExW` **之前**初始化。
2. `RegisterClassExW.restype = wt.ATOM`、`argtypes = [POINTER(_WCX)]`；`CreateWindowExW` 的 `hInstance` 用 `ctypes.c_void_p`。
3. 创建失败立即 `raise ctypes.WinError()`，并对 NIM_ADD 失败 `DestroyWindow` 不留半初始化窗口。

## 验证记录

- [x] 单元、集成或端到端测试：`tests_py/test_menu_tray.py` 20 项 + 全量 pytest 通过（2026-11-11）。
- [x] 启动或手动回归：真机托盘注册 `tray_added=true`、`Shell_NotifyIconGetRect` rc=0；左键单击显隐一次、右键只开菜单的验收脚本全绿。
- [ ] 格式化或静态检查：不适用。
- [ ] 类型检查或编译：不适用。
- [ ] 构建：不适用。

## 可复用规则

- 凡 ctypes WNDPROC/回调式 Win32 创建：**先初始化全部回调可见状态，再调用创建函数**。
- 「创建返回 NULL 且 err=0」的第一怀疑对象是回调内抛异常，而不是系统/权限；可在回调里加 try/except 落日志自证。
- x64 句柄/HINSTANCE 一律显式 `argtypes` + `c_void_p`，别信裸 int。

## 适用范围与不适用范围

- 适用：ctypes/pywin32 手写 WNDPROC 的隐藏窗口、托盘宿主窗、消息-only 窗口改造。
- 不适用：高层框架（pywebview/Qt）自管窗口过程的路径；但「回调早于构造完成」这类顺序坑在其它语言同样存在。

## 剩余风险

- 回调内其它未初始化字段仍可能以同样方式静默失败；新增字段时必须同步检查初始化顺序。

## 关联

- 相关记录：[[踩坑-CreateMutexW后未紧邻读GetLastError致单实例守卫静默失效]]、[[踩坑-Win11托盘图标在独立溢出窗口且取证须先设DPI-aware]]
- 相关分类：03-通用/04-工程规范与安全
- 相关代码、命令或文档：G:\cc-hud\cchud_next\tray.py、G:\cc-hud\tools\tray_click.py