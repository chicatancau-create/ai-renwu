---
title: "DevEco 命令行 hvigor 构建两坑：缺 DEVECO_SDK_HOME 报 00303217、unsigned WARN 致假 exit 1"
date: 2026-11-16
domain: common
category: 03-调试与验证
status: verified
severity: medium
stack: [HarmonyOS, ArkTS, DevEco Studio, hvigor, PowerShell]
tags: [构建, 退出码, stderr, SDK]
---

# 问题：DevEco 命令行 hvigor 构建两坑：缺 DEVECO_SDK_HOME 报 00303217、unsigned WARN 致假 exit 1

> 复现、定位、修复、验证均已完成（机制一层留有未做对照实验的推断，已单独标明）。

## 一句话结论

本机命令行跑 `hvigorw.js assembleHap` 必须先给 `DEVECO_SDK_HOME` 环境变量（或 local.properties 的 `hwsdk.dir`），否则 ERROR 00303217 直接失败；构建成功后 unsigned 签名 WARN 走 stderr，`2>&1` 合并时工具会话报 exit 1——红绿只认 stdout 的 `BUILD SUCCESSFUL` / `ERROR` 行，不认退出码。

## 触发条件与影响

- 项目或功能：Harmony/ShoppingMallApp（DevEco 新建模板工程，signingConfigs 为空）命令行编译验证
- 环境与版本：DevEco Studio 装于 `D:\DevEco Studio`（自带 `tools\node\node.exe` + `tools\hvigor\bin\hvigorw.js`）；PS 5.1 工具会话
- 触发条件：①新 shell 未设 DEVECO_SDK_HOME 且工程 local.properties 无 hwsdk.dir；②构建成功但 stderr 有 WARN 且命令用了 `2>&1`
- 影响范围：①构建直接失败；②成功构建被误判为失败，可能引发无谓排错或重复构建

## 复现步骤

1. 前置条件：工程 local.properties 无 hwsdk.dir、环境无 DEVECO_SDK_HOME
2. 操作或命令：`& 'D:\DevEco Studio\tools\node\node.exe' 'D:\DevEco Studio\tools\hvigor\bin\hvigorw.js' assembleHap --mode module -p product=default --no-daemon`
3. 预期结果：BUILD SUCCESSFUL
4. 实际结果：①`ERROR 00303217 Invalid value of 'DEVECO_SDK_HOME'`；②补环境变量后 stdout 末尾 `BUILD SUCCESSFUL in 8 s 799 ms` + `33 tasks in total`，但会话报 `[exit code: 1]`

## 证据

- 2026-11-15 鸿蒙作业1：未设 env 首跑报 00303217；加 `$env:DEVECO_SDK_HOME='D:\DevEco Studio\sdk'` 并在 local.properties 写 `hwsdk.dir=D:\\DevEco Studio\\sdk` 后 BUILD SUCCESSFUL
- 2026-11-16 章5/章6/章8 三次构建：stdout `BUILD SUCCESSFUL in 12 s / 7 s 900 ms / 8 s 799 ms` 与 `[exit code: 1]` 同现；stderr 内容为 signingConfigs 空 → unsigned HAP 的 WARN
- 产物存在：`entry/build/default/outputs/default/entry-default-unsigned.hap`

## 根因分析

- 已确认的根因①：hvigor 从 DEVECO_SDK_HOME 环境变量或 local.properties hwsdk.dir 取 SDK 路径；新建模板工程不写 hwsdk.dir，IDE 内构建由 IDE 自供所以不报
- 已确认（现象层）②：exit 1 与 stderr WARN 同现、stdout 成功标记齐全；改认 stdout 后连续四次构建红绿判断正确
- 推断（未验证）：PS 5.1 的 `2>&1` 把 stderr 行包成 ErrorRecord 触发会话错误偏好提前终止致 exit 1；未做不合并 stderr 的对照实验
- 问题归属：环境或依赖

## 最小修复

- 构建命令前置 `$env:DEVECO_SDK_HOME='D:\DevEco Studio\sdk'`（或 local.properties 写 hwsdk.dir，反斜杠双写）
- 红绿判据改认 stdout 的 `BUILD SUCCESSFUL` / `ERROR` 行；exit 1 + SUCCESSFUL 记为成功
- 未改项目代码、未改签名配置（unsigned 仅编译验证用途）

## 验证记录

- [x] 构建：修复后四次 BUILD SUCCESSFUL（11-15 作业1、11-16 章5/章6/章8）
- [x] 启动或手动回归：产物 unsigned hap 生成（仅编译验证，未上设备）
- [ ] 不合并 stderr 的对照实验：未跑，exit 1 机制保持推断
- [ ] 模拟器/真机回归：未跑（本机模拟器无系统镜像）

## 可复用规则

1. 本机命令行跑 hvigorw.js 前先查 DEVECO_SDK_HOME / hwsdk.dir；缺就补 `'D:\DevEco Studio\sdk'`（安装路径属易变项，用前实测复核）
2. hvigor 及任何会往 stderr 写 WARN 的原生命令，在 `2>&1` 合并时不以退出码判红绿，认 stdout 的成功/失败标记行
3. 例外：配置了签名、stderr 干净时退出码可用；本规则不豁免 stdout 里真实的 ERROR 行

## 适用范围与不适用范围

- 适用：本机 DevEco 命令行构建 + PS 5.1 工具会话
- 不适用：IDE 内构建（IDE 自供 SDK 路径）；pwsh 7 或其他错误偏好的 shell 需另测

## 剩余风险

- exit 1 机制未做对照实验；DevEco 升级若改 SDK 目录名需重测路径
- unsigned hap 不能上真机，签名验证不在本记录覆盖内

## 关联

- 相关记录：[[踩坑-本机执行环境六个静默陷阱-PS反引号wmic缺失pythonw无stdout]]（无害 stderr 同族）；[[01-前端/04-框架与组件/ArkTS-Styles块只接受通用属性-fontSize与fontColor会编译失败]]（同款命令行构建）
- 相关分类：03-通用/03-调试与验证
- 相关代码、命令或文档：`G:\AIrenwu\01_任务归档\2026-11-15_课程作业档案\01_报告\鸿蒙-档案.md`（构建命令节）
