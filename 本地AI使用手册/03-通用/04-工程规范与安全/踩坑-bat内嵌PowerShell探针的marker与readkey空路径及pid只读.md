---
title: "bat 内嵌 PowerShell 探针：marker 选 rem~、readkey 空路径、$pid 只读、YAML 缩进自适应"
date: 2026-11-11
domain: common
category: 工程规范与安全
status: verified
severity: medium
stack: [cmd, PowerShell 5.1, GBK bat]
tags: [bat, PowerShell, 内嵌, 编码]
---

# 问题：bat 内嵌 PowerShell 探针的四个坑（marker / readkey 空路径 / $pid / 缩进）

## 一句话结论

GBK bat 内嵌 PowerShell 探针用 `rem~` 前缀 + `findstr /b /c:"rem~"` + `delims=~` 释放；用 `rem#` 会把注释行的 `#` 当分隔符吃掉致 PS 把注释当命令；`:readkey` 空路径要 `if "%~1"=="" exit /b` 否则报「'/b' 不是内部或外部命令」；PS 里 `$pid` 只读要改名；往 YAML 插规则要读 `rules:` 下一行的实际缩进。

## 触发条件与影响

- 环境：Windows PowerShell 5.1，GBK+CRLF 的 fix-network.bat，内嵌探针释放到 %TEMP% 执行。
- 触发：单文件 bat 携带 PowerShell 探针 / 解析 YAML 配置。

## 证据（2026-11-11 fix-network.bat v2.2→v2.4 实测）

- `rem#`+`delims=#`：首行 `# 注释` 的 `#` 被当分隔符，PS 报「无法将...识别为 cmdlet」。改 `rem~`+`delims=~` 后正常。
- `:readkey` 传空路径（FlClash 无 verge.yaml）：`if not exist %~1 exit /b` 解析异常报「'/b' 不是...」；加 `if "%~1"=="" exit /b` 修复。
- PS 用 `$pid` 赋值报「变量只读」；改 `$profId`。
- FlClash profile 规则缩进 4 空格、config.yaml 2 空格；写死缩进会破坏 YAML；读下一行 `^(\s*)- ` 自适应。

## 根因分析

- `for /f delims=#` 把行内所有 `#` 当分隔符，注释首字符被吞。
- cmd 对 `if not exist <空>` 的解析产生杂散 `/b`。
- `$PID` 是 PowerShell 自动只读变量。
- YAML 列表缩进必须与同级一致。

## 最小修复

- marker 用 `rem~`；readkey 先判空；PS 变量避开 `$pid`/`$args` 等自动变量；插 YAML 前读实际缩进。

## 验证记录

- [x] v2.4 check/fix 冒烟通过，探针正常释放、YAML 校验通过。

## 可复用规则

- 单文件 bat 内嵌 PS：marker 选不会出现在内容里的字符（`~`），别用 `#`/`|`。
- 任何 `:sub` 接收路径参数先 `if "%~1"=="" exit /b`。
- 写 YAML 列表项前读同級缩进；改完用 YAML parser 校验。

## 适用范围与不适用范围

- 适用：GBK bat + PS 5.1 单文件工具。
- 不适用：纯 PS 脚本（无 cmd 解析层）。

## 剩余风险

- 探针内容若含 `~` 行首仍会被误提取，marker 需与内容互斥。

## 关联

- [[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]
- [[踩坑-cmd入口脚本判管理员与choice默认键取值]]
- [[踩坑-Bash内联传参吞PowerShell变量与反斜杠]]
