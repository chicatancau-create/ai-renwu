---
title: "CreateMutexW 之后没有紧邻读 GetLastError，单实例守卫静默失效"
date: 2026-10-14
domain: common
category: 03-通用/04-工程规范与安全
status: verified
severity: high
stack: [C++, Win32, Windows]
tags: [单实例, 并发, GetLastError, 静默失效]
---

# 问题：写了单实例守卫，但同一时间跑起了两个进程，且没有任何报错

## 一句话结论

`CreateMutexW` 与 `GetLastError()` 之间夹了一个 `if (!handle) return false;` 判断，
最后错误码在这中间被覆盖，守卫**永远返回"没有别的实例"**。必须把 `GetLastError()` 提到紧邻的下一条语句。

## 触发条件与影响

- 项目或功能：托盘应用（无主窗口）的单实例保护。
- 环境与版本：Win11 + MSVC 14.44 + Qt 6.8.3。
- 触发条件：连续启动两个实例。
- 影响范围：多实例各自注册全局热键、各自写同一份历史目录。对截图/贴图类工具，
  表现为"热键时灵时不灵""贴图列表串台"这类极难归因的症状。而且**没有任何失败信号**。

## 复现步骤

1. 前置条件：守卫代码形如
   ```cpp
   g_lock = CreateMutexW(nullptr, TRUE, L"Local\\App.SingleInstance.v1");
   if (!g_lock) return false;
   return GetLastError() == ERROR_ALREADY_EXISTS;   // ← 中间隔了一条语句
   ```
2. 操作或命令：起第一个实例，再起第二个，然后数进程数。
3. 预期结果：第二个退出，进程数 1。
4. 实际结果：第二个照常跑起来，进程数 2。

## 证据

发现方式是**顺带的**：给任务栏做 UIA 枚举时，`TaskListButtonAutomationPeer` 里出现了两条本应用记录，
`taskkill` 一次性报出两个 PID：

```
成功: 终止进程 "MyTrayApp.exe"，其 PID 为 32624。
成功: 终止进程 "MyTrayApp.exe"，其 PID 为 5328。
```

修复后跑 `test-single-instance.ps1`：

```
SECOND_EXITCODE=3
SECOND_WROTE_JSON=False
ALIVE_COUNT=1
```

## 根因分析

- 已确认的根因：`GetLastError()` 返回的是**调用线程最近一次 API 调用的错误码**，
  任何夹在中间的 Win32 调用（包括 CRT 内部调用）都可能改写它。判空分支本身不是 API 调用，
  但编译器插入的栈检查 / CRT 调用可以。所以这是**时序脆弱**而非必然错误——
  这也解释了为什么它"有时看起来是对的"。
- 排除过的假设：不是 `Local\` 前缀的命名空间问题（同一会话内该前缀可见，且修复后立刻生效）；
  不是句柄被提前 `CloseHandle`（句柄存在静态变量里，进程生命周期内不关）。
- 问题归属：本次修改引入。

## 最小修复

```cpp
g_instanceLock = CreateMutexW(nullptr, TRUE, L"Local\\MyTrayApp.SingleInstance.v1");
const DWORD lastError = GetLastError();   // 紧邻下一条语句，中间不插任何逻辑
if (!g_instanceLock)
    return false;
return lastError == ERROR_ALREADY_EXISTS;
```

## 验证记录

- [x] 编译：MSVC 14.44 零警告零错误。
- [x] 端到端：`test-single-instance.ps1` 断言第二实例退出码 3、不落 JSON、存活数 1。
- [x] 反向：修复前同一脚本能观察到 2 个进程并存。

## 可复用规则

**凡是"调用 A → 依据 A 的错误码判断"的模式，`GetLastError()` 必须是紧随 A 的第一条语句，
并且立刻存进局部变量；后续分支只用这个变量。**
推论：**静默失效的守卫只能靠"数进程 / 数连接 / 数锁"这类外部计数来发现**，
不要指望它自己报错。所以带单实例守卫的程序，验收里要有一条显式的"起两次看进程数"。

## 适用范围与不适用范围

- 适用：Win32 上所有依赖 `GetLastError` 的判据（`CreateMutex`/`CreateEvent`/`FindFirstFile`/`RegOpenKeyEx` 等）。
- 不适用：C++ 异常体系、`std::error_code`；跨会话的全局命名空间（`Global\` 需要额外权限，是另一个问题）。

## 剩余风险

本轮只在同一用户会话内验证；`Global\` 命名空间下的跨会话行为未测试。
另外，第二实例被守卫挡掉时**不写任何日志**（只返回退出码 3），如果将来要排查"用户说点了没反应"，
需要补一条日志输出。

## 关联

- 相关记录：[[踩坑-cmd入口脚本判管理员与choice默认键取值]]（同为"判据取错来源导致静默走错分支"）
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码、命令或文档：来源工程已于 2026-10-15 删除，无可跳转路径（结论仍由当时的自产证据支撑）
