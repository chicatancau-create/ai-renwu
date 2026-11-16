---
title: "Get-ChildItem 的 -Include 配 -LiteralPath 不过滤，会连不该删的文件一起删"
date: 2026-11-16
domain: common
category: "调试与验证"
status: verified
severity: medium
stack: ["PowerShell 5.1", "Windows 11"]
tags: ["powershell", "Get-ChildItem", "Include", "删除脚本", "过滤", "清理"]
---

# 问题：`-Include` 不生效，删除脚本按扩展名筛文件会筛出全部文件

## 一句话结论

`Get-ChildItem -LiteralPath <目录> -Recurse -Include *.log, *.etl` **完全不过滤**，返回目录下所有文件；
`-Recurse` 救不了它。要按扩展名筛必须自己写 `Where-Object { $_.Extension -in '.log', '.etl' }`
（或把路径写成带通配的 `-Path`）。写"只删某几类文件"的脚本时，**命中集合必须与扩展名分布交叉核对**，
否则会静默多删。

## 触发条件与影响

- 项目或功能：`脚本库\10_清理与空间回收\system_cleanup_worker.ps1`（清理 `C:\Windows\Logs`，只删 `.log/.etl/.txt/.cab/.old`）
- 环境与版本：本机 `pwsh` 实为 **Windows PowerShell 5.1.28000.3086（Desktop）**；Windows 11 Pro 10.0.28000
- 触发条件：`-Include` 与 **`-LiteralPath`** 同时使用（`-LiteralPath` 不做通配解析，`-Include` 因此失去过滤锚点）
- 影响范围：所有"按扩展名/模式挑了再删/再移动"的 PowerShell 脚本；后果是**多删**，且因为 DryRun 也会多报，
  DryRun 看起来"自洽"就更难发现

## 复现步骤

1. 前置条件：`C:\Windows\Logs` 存在（实测 237 个文件：`.etl` 202 + `.log` 19 + `.json` 11 + `.xml` 5）
2. 操作或命令：

```powershell
# 期望只命中 .log/.etl 等 5 类（应 221 个）
(Get-ChildItem -LiteralPath 'C:\Windows\Logs' -Recurse -Force -File `
  -Include *.log, *.etl, *.txt, *.cab, *.old -ErrorAction SilentlyContinue).Count
```

3. 预期结果：`221`
4. 实际结果：**`237`**（等于该目录全部文件数，`.json`/`.xml` 也被算了进去）

## 证据

同一目录、同一时刻的两种写法对照：

| 写法 | 命中数 | 说明 |
|---|---|---|
| `-LiteralPath ... -Recurse -Include *.log,*.etl,*.txt,*.cab,*.old` | **237** | 全部文件，过滤没生效 |
| `Get-ChildItem -LiteralPath ... -Recurse -Force -File \| Where-Object { $_.Extension -in '.log','.etl','.txt','.cab','.old' }` | **221** | 正确的 221 |

差值 16 = `.json` 11 + `.xml` 5，与该目录扩展名分布完全对上——这条对账就是判据。

改完后脚本 DryRun 输出从「可删 237 个 / 28.5 MB」变为「可删 **221 个 / 27.3 MB**」，与扩展名分布一致。

## 根因分析

- 已确认的根因：`-Include` 的过滤只在**路径本身参与通配展开**时生效；`-LiteralPath` 明确表示"按字面路径、不做通配"，`-Include` 便无从附加过滤，参数被静默忽略（不报错、不警告）。
- 排除过的假设：不是 `-Force`／`-ErrorAction`／`-File` 的影响（这几个开关在两种写法里完全相同）；
  也不是路径里含 `$` 或中文导致（`C:\Windows\Logs` 两者都没有）。
- 问题归属：修改前已有（第一版脚本就是这么写的，是我在 DryRun 数字对不上扩展名分布时才发现的）

## 最小修复

```powershell
# 改前（错）
$targets = @(Get-ChildItem -LiteralPath $p -Recurse -Force -File -Include *.log, *.etl, *.txt, *.cab, *.old -ErrorAction SilentlyContinue)

# 改后（对）
$targets = @(Get-ChildItem -LiteralPath $p -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in '.log', '.etl', '.txt', '.cab', '.old' })
```

不影响任何接口/配置；只改筛选方式，命中的是同一批文件的正确子集。

## 验证记录

- [x] 静态检查：两种写法在同一目录、同一时刻对照，计数 237 vs 221，差值可由扩展名分布（`.json` 11 + `.xml` 5）完全解释
- [x] 手动回归：`system_cleanup_worker.ps1 -DryRun` 重跑，输出 221 个 / 27.3 MB
- [ ] 真实删除：**未跑**——本轮会话非管理员，删 `C:\Windows\Logs` 必然失败（实测 `Remove-Item` 报
      `ArgumentException` + `Access to the path is denied.` + HRESULT `0x80070057`）。真删由
      `run-system-cleanup.cmd` 提权后执行，结果待补记
- [ ] 其它 PowerShell 版本（7.x）未测

## 可复用规则

1. **凡"按模式挑一批文件再删/再移"的脚本，先打印命中集合的大小与该目录的扩展名分布，两者对得上才允许真删。**
   DryRun 与真删共用同一段筛选代码，所以 DryRun 多报＝真删会多删。
2. PowerShell 里按扩展名筛，一律用 `Where-Object { $_.Extension -in '...' }`；不要用 `-Include` 配 `-LiteralPath`。
   确实要用 `-Include`，就得把路径写成通配形式（`-Path "$dir\*" -Recurse -Include *.log`）。
3. 危险脚本的"只删这些"承诺必须能在 DryRun 输出里被**独立数据**证伪（本例靠扩展名分布），
   不能只靠脚本自己说"我筛的是这几类"。

## 适用范围与不适用范围

- 适用：Windows PowerShell 5.1 / PowerShell 7 的 `Get-ChildItem`；同样适用于 `Copy-Item`/`Remove-Item`/`Get-ChildItem`
  等一组共用 `-Include` 语义的 cmdlet
- 不适用：`-Path` 带通配符的调用（那是 `-Include` 的正确用法，会正常过滤）；`robocopy /XF`、`gci -Filter`（`-Filter`
  是文件系统层过滤，只支持单个模式，语义不同）

## 剩余风险

- `-Filter` 与 `-Include` 行为不同（`-Filter` 快但只接受一个模式，且不支持多扩展名列表），本记录**未**对 `-Filter` 做 A/B。
- 若目录内含 junction/symlink，`Get-ChildItem -Recurse` 会跟随，可能删到目录外的真源（本机踩过），
  本记录未覆盖该情形，需另加 `-Attributes !ReparsePoint` 之类的护栏。
- PowerShell 7.x 的行为未在本机验证（本机只有 5.1）。

## 关联

- 相关记录：[[规则-清理归档前先反查三类引用]]（删除前必查计划任务/脚本引用/回滚点）、
  [[踩坑-cmd入口脚本判管理员与choice默认键取值]]（同一套提权清理工具的另一半）、
  [[踩坑-Bash内联传参吞PowerShell变量与反斜杠]]（同属"命令看起来对、实际被静默改写"家族）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]、[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码、命令或文档：`G:\AIrenwu\脚本库\10_清理与空间回收\system_cleanup_worker.ps1`、
  `G:\AIrenwu\01_任务归档\2026-11-15_清理归档\01_报告\清理与归档报告.md`（12.3 节）
