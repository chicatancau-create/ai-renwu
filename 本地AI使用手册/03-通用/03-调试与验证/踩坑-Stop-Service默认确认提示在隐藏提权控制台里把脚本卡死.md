---
title: "Stop-Service 默认弹确认，在看不见的提权控制台里把整条脚本卡死（无输出、无超时、无报错）"
date: 2026-11-04
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Windows, PowerShell 5.1]
tags: [提权脚本, Stop-Service, ConfirmImpact, 静默卡死, sc.exe]
---

# 问题：提权脚本里用 `Stop-Service`，进程活着、日志空、永远不返回

## 一句话结论

`Stop-Service` 的 `ConfirmImpact='High'` 且默认 `$ConfirmPreference='High'` ⇒ **它会等一次键盘确认**；
当这个 powershell 是我用 `Start-Process -Verb RunAs` 起的（窗口不在我的可见范围里），
确认提示就落在一个没人看的控制台，脚本表现为「卡住」：不报错、不超时、不产出。

## 触发条件与影响

- 环境：Windows 11 28000 + Windows PowerShell 5.1，提权子进程由脚本启动
- 触发条件：`Stop-Service -Name X -Force`（`-Force` 只压「依赖服务」提示，**不压确认提示**）
- 影响范围：整条流水线停在那一行；上游 `-Wait` 的调用方跟着挂着。
  本轮我因此在 10:47–10:55 白等了 8 分钟

## 复现步骤

1. 前置：`Start-Process powershell -Verb RunAs -Wait -ArgumentList '-File','worker.ps1'`
2. worker.ps1 内某一行是 `Stop-Service -Name clash_verge_service -Force`
3. 预期：服务停止、脚本继续
4. 实际：控制台停在「继续进行吗? Y/N」，父调用方一直 `-Wait`，无任何输出文件

## 证据

排除法给出的定位（都是本轮实测）：

- worker 的备份步骤**已完成**（`verge-service-bak\` 里有 3,379,200 B 的旧二进制 + `active-owner.json.OLD`，mtime 10:47:29）
- 之后一步全无痕迹：**服务仍是 `Running`、PID 没变（12840）**，`Get-Process` 查不到任何
  `clash-verge-service-uninstall.exe` 进程，SCM 事件日志近 15 分钟**零条停止事件**
  ⇒ 卡点被夹在「备份」与「卸载器」之间，正好是 `Stop-Service` 那一行
- 提权 worker 进程存在但读不到（父上下文的 `Win32_Process.CommandLine` 为空），存活 6 分钟以上

第二次改走 `sc.exe stop` + 轮询，同一台机同一服务 **2 秒内就 `Stopped`**，反证第一次不是服务起不来。

## 根因分析

- 已确认根因：交互式确认提示无人应答（`Stop-Service` 属 `ConfirmImpact=High` cmdlet）
- 排除过的假设：①服务拒绝停止 —— 换 `sc.exe stop` 立刻成功，否；
  ②UAC 弹窗没点 —— 提权已经成功（脚本打出 `管理员=True`），否；
  ③`Get-FileHash` 之类慢操作 —— 它在卡点之前且日志有产出，否
- 问题归属：**本次修改引入**（我的脚本写法）

## 最小修复

三选一，按稳妥度排序：

```powershell
Stop-Service -Name X -Force -Confirm:$false     # 显式压掉确认
& sc.exe stop X                                 # 原生工具，根本不提示（推荐用于脚本）
$ConfirmPreference = 'None'                     # 整脚本范围内关掉（会同时关掉别的确认，慎用）
```

配套的**流程**修正（比换 cmdlet 更重要）：

1. 提权 worker 必须**逐行增量落盘**：`[IO.File]::AppendAllText($LOG, ...)`，
   而且 `Say` 里同时 `Write-Host`。
   我第一版是「跑完再 `WriteAllText`」，于是卡住时日志文件压根不存在，什么也看不见。
2. 启动器**不要 `-Wait`**：让它在后台跑，我这边轮询日志文件；
   这样卡住能第一时间发现，而不是被超时吞掉。
3. 停止服务后用**轮询代替固定 Sleep**：`for ($i=1..12) { Start-Sleep 2; if (状态到位) {break} }`，
   把每次轮询结果写进日志（本轮就是靠这 12 行日志确认「第 1 次轮询: 服务=Stopped」）。

### 同一族还有两个「静默失败」，本轮实际各撞一次

**A. 报错只落在看不见的控制台 ⇒ 表现为「日志缺行」，而不是报错。**
重装完那一步我要打印两份服务二进制的 SHA256，`Get-FileHash` 在服务刚起、文件被占用时抛异常；
因为 `$ErrorActionPreference='Continue'`，异常只写进那个提权控制台（我看不到），
`Say` 那一行整条没落盘 —— 日志从「验证」标题直接跳到最终状态。**我差点把「没打印」当成「没问题」**，
是回看日志缺行才发现第 4 步少了两行，补做独立复核才拿到哈希。

- 规则：提权 worker 里**每个可能失败的调用都要 `2>&1` 并进日志**，或把 `$ErrorActionPreference` 设 `Stop`
  并在外层 `try/catch` 把异常文本 `AppendAllText` 落盘；
- 判据：**按脚本的步骤数核对日志行数**，缺行＝那一步没成功，别默认它静默通过。

**B. 比较断言两侧都取到空值时，`-eq $true` 是假绿。**
我用 `(Get-Acl).Access | ForEach-Object { $_.IdentityReference + ':' + $_.AccessControlType }` 拼 ACL 文本，
拼出来是**空串**，于是 `ACL 一致=True` 毫无意义。改用 `icacls <文件>` 打印原文才拿到
`SYSTEM:(I)(F)` / `Administrators:(I)(F)` 两行真实数据。

- 规则：**比较类断言必须把两侧原文各打印一遍**，两侧皆空（或皆 `NA`/`$null`）时的 `True` 一律不计入证据；
- 附带：读 `C:\ProgramData` 下的 ACL 需要提权，非提权时 `icacls` 会回「拒绝访问」而不是空 —— 见
  [[踩坑-无权限读ProgramData被当成文件不存在致误删服务拆掉内核]]。

## 验证记录

- [x] 同一服务用 `sc.exe stop` 重跑：10:55:39 发起 → 10:55:41 第 1 次轮询即 `Stopped`，后续步骤全部走完
- [x] 增量日志生效：第二次运行每一步都有带时间戳的行，卡点可即时判读
- [x] 残留清理：新脚本按 `CommandLine -like '*verge_fix.ps1*'` 精确收掉上一轮挂住的提权进程
- [x] 静默失败 A 复核：独立重跑哈希校验，拿到两份 SHA256 相同（`56D68AFD…9AB3`）的真实输出
- [x] 静默失败 B 复核：`icacls` 打印两份内核的 ACL 原文一致，替换掉那条假绿断言

## 可复用规则

**凡脚本化操作 Windows 服务，一律 `sc.exe stop/start` 或显式 `-Confirm:$false`；
提权 worker 一律增量落盘 + 启动器不 `-Wait` + 状态用轮询判定。**
配套三条同族纪律（本轮各实测一次）：
①**可能失败的调用一律 `2>&1` 进日志**，并按步骤数核对日志行数 —— 缺行＝没成功；
②**比较类断言要打印两侧原文**，两侧皆空时的 `True` 不算证据（用 `icacls` 替掉拼不出来的 `Get-Acl`）；
③**「某文件没有副本」这类否定断言要先按 文件名+尺寸+mtime 具名搜盘**，别凭「别处没见过」下结论。
适用条件：任何非交互执行的 PowerShell。
例外：交互式人工敲命令时，`Stop-Service` 的确认反而是安全带，别在人手操作的脚本里全局关确认。

## 适用范围与不适用范围

- 适用：`Start-Process -Verb RunAs`、计划任务、CI runner、任何无人值守 PowerShell
- 不适用：人手在可见终端里操作（那时提示是功能不是故障）
- 同类坑（同一族「无人应答的交互」）：`Remove-Item` 对只读/系统属性的确认、
  `sc delete` 后服务标记延迟、`format` 类命令的 y/N

## 剩余风险

`sc.exe` 不返回退出码语义（打印的 `WIN32_EXIT_CODE` 是人看的），脚本里判成败仍需回读服务状态 —— 本条已按该写法执行。
另：`-Verb RunAs` 起的提权控制台**看不见也关不掉**（非提权侧 `Stop-Process` 静默失败、`Win32_Process.CommandLine`
读成空），所以「提权脚本卡住」只能靠**日志文件是否还在长**来判断；本轮我按 `CommandLine -like '*verge_fix.ps1*'`
在提权侧自杀式清理，这个匹配串要在脚本名变更时同步改，否则会误杀或漏杀。

## 关联

- 相关记录：[[踩坑-App自更新后手动重装服务会装旧二进制且卸载器删内核致静默降级Sidecar]]（发现本条的那次修复）、
  [[踩坑-无权限读ProgramData被当成文件不存在致误删服务拆掉内核]]、
  [[踩坑-执行环境Start-Process子进程在工具会话结束时被连带回收]]
- 相关分类：03-通用/03-调试与验证
- 本机产物：`%TEMP%\verge_fix2.txt`（`sc.exe stop` 那次的逐行日志）
