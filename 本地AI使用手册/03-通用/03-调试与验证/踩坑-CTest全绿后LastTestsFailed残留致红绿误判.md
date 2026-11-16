---
title: "CTest 全绿后 LastTestsFailed.log 仍残留，按它判当前红绿必误判"
date: 2026-11-12
domain: common
category: 03-调试与验证
status: verified
severity: medium
stack: [CMake, CTest, Qt]
tags: [ctest, 测试判读, 残留文件, 假失败]
---

# 问题：CTest 全绿后 LastTestsFailed.log 仍残留，按它判当前红绿必误判

## 一句话结论

CTest 在一次**全部通过**的运行后**不会删除** `Testing/Temporary/LastTestsFailed.log`；该文件只记录「上一次有失败的运行」，看到它存在就判「当前是红的」必然误判。判本轮结果只看 `LastTest.log` 的 mtime 与 ctest stdout 的 `tests passed` 行。

## 触发条件与影响

- 项目或功能：任何用 CTest 的工程（本机为 CodeWeave 应用端 Qt 门禁）。
- 环境与版本：Windows + CMake/Ninja + CTest（Qt 6.8.3 门禁脚本 `工程文件/工具/构建当前Qt.cmd`）。
- 触发条件：构建树里曾经有过一次失败运行，之后又跑了一次全绿运行。
- 影响范围：审查/验收方读构建树判红绿；自动化脚本若以「失败日志存在」为判据会永久报红。

## 复现步骤

1. 前置条件：某次 CTest 运行有失败项（留下 `LastTestsFailed.log`）。
2. 操作：再跑一次全绿运行（`cmd /d /c 工程文件\工具\构建当前Qt.cmd`）。
3. 预期：失败日志被清除或更新为空。
4. 实际：`LastTestsFailed.log` 原样保留，内容与 mtime 都停在上一次失败。

## 证据

- 2026-11-09 与 2026-11-12 两次独立复现：`LastTest.log` mtime 为当轮（11-12 09:59:18），ctest stdout 为 `100% tests passed, 0 tests failed out of 11`；同目录 `LastTestsFailed.log` mtime 为 **11-11 20:53:15**、内容 `8:qt-qml-load`，而当轮 #8 实际 `Passed 7.74 sec`。
- 审查方曾两次据此误报「当前门禁是红的」，均靠比对两个文件 mtime 纠正。

## 根因分析

- 已确认的根因：CTest 只在有失败时写 `LastTestsFailed.log`，成功运行不触碰它（CMake/CTest 行为，非本工程脚本问题）。
- 排除过的假设：不是「本轮真的失败」；不是脚本漏删（脚本根本不管该文件）。
- 问题归属：环境或依赖（CTest 固有行为）。

## 最小修复

不改 CTest。改**判读规则**：
1. 判本轮红绿只认 ctest stdout 的 `N% tests passed, M tests failed out of K` 与 `LastTest.log` 的 mtime 是否等于本轮。
2. 若必须读 `LastTestsFailed.log`，先比它与 `LastTest.log` 的 mtime；前者更旧即残留，忽略。
3. 自动化门禁脚本不要以该文件存在作为失败判据。

## 验证记录

- [x] 格式化或静态检查：不适用。
- [x] 类型检查或编译：门禁含 Release 构建，通过。
- [x] 单元、集成或端到端测试：11/11 通过（126.14s），与残留日志内容矛盾已核实。
- [x] 构建：通过。
- [x] 启动或手动回归：比对两文件 mtime + 当轮 #8 结果，确认残留。

## 可复用规则

读任何「上次失败」类残留文件前，先比它与「本次运行日志」的 mtime；更旧即残留。适用于 CTest、以及一切「只写不清」的失败标记文件。例外：若工具明确文档化「成功即清空」，以实测为准再下结论。

## 适用范围与不适用范围

- 适用：CTest 构建树红绿判读；审查/验收读他人构建树。
- 不适用：CI 上以退出码为准的场景（退出码不受残留文件影响）。

## 剩余风险

若有人手工删除 `LastTest.log` 而留下失败日志，mtime 判据失效；此时以重新跑一次门禁为准。

## 关联

- 相关记录：[[踩坑-QML警告采集只覆盖创建期窄窗绑定警告漏报]]（同轮审查的另一判读坑）
- 相关分类：03-调试与验证
- 相关代码、命令或文档：`工程文件/工具/构建当前Qt.cmd`；`构建产物/qt/current/Testing/Temporary/`
