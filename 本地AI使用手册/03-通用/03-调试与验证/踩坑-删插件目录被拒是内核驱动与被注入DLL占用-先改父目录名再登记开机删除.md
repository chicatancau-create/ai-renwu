---
title: "删应用插件目录报「访问被拒绝」不一定是权限不够：目录里可能有正在运行的内核驱动服务 .sys，也可能是已被注入其它进程的 .dll"
date: 2026-11-20
domain: common
category: 调试与验证
status: verified
severity: medium
stack: ["Windows 10/11", "PowerShell 5.1", "Python ctypes", "sc.exe", "OpenRevo 0.9.8"]
tags: ["Remove-Item", "访问被拒绝", "内核驱动服务", "RTCoreMini64", "DLL注入", "MoveFileEx", "MOVEFILE_DELAY_UNTIL_REBOOT", "RunOnce", "目录改名"]
---

# 问题：整个插件目录删不掉，一直报「对路径 xxx 的访问被拒绝」

## 一句话结论

删除一个带原生二进制的应用（本例是 OpenRevo 的 `mro-hud` 插件）时，`Remove-Item -Recurse` 的「访问被拒绝」有**三层完全不同的原因**：①宿主按 `service.auto_start` 不停把伴随 exe 拉起来；②目录里的 `.sys` 已经被 `sc create` 注册成**内核驱动服务且正在 Running**；③目录里的 `.dll` 被全局钩子**注入到别的进程**（连 `svchost.exe` 里都有）。**先把父目录整体改名移走**可以让应用立刻「看不见」这个插件，再逐项处理锁文件。

## 触发条件与影响

- 项目或功能：删除 OpenRevo 插件 `mro-hud`（内含 RTSS 运行时 `rtss\`）
- 环境与版本：Windows（ZHOUMO\Admin，Medium 完整性会话 + `Start-Process -Verb RunAs` 静默提权）、OpenRevo v0.9.8
- 触发条件：`Remove-Item 'C:\Users\<user>\AppData\Roaming\OpenRevo\plugins\mro-hud' -Recurse -Force`
- 影响范围：删到一半停下会留下半残目录，宿主可能继续按 manifest 拉起服务；用户以为「已经删了」其实还在

## 复现步骤

1. 插件目录里带 `agent\xxx.exe`（manifest 声明 `service.auto_start`）→ 第一次删除报 `对路径 ...mro_agent.exe 的访问被拒绝`（宿主反复拉起，`Get-Process` 能看到 PID 一直变）
2. 继续删到 `rtss\PlugIns\Client\RTCoreMini64.sys` → 又报访问被拒绝。用 `Get-CimInstance Win32_Service | ? Name -like 'RTCore*'` 查得 **`RTCoreMini64` 状态 Running**，`PathName` 正是插件目录里那个 `.sys`
3. 处理完驱动后再删 `rtss\RTSSHooks64.dll` → 仍报访问被拒绝。用
   `Get-Process | %{ $_.Modules | ? FileName -like '*mro-hud*rtss*' }` 查出持有者：`pwsh`、`python`、**`svchost.exe`**
4. 预期结果：目录删干净
5. 实际结果：`svchost.exe` 不能杀，`.dll` 永远删不掉

## 根因

- Windows 不允许删除「已映射到任意进程地址空间」的 PE 文件（`.exe`/`.dll`/`.sys` 都算）；这跟 ACL 权限无关，所以「以管理员重试」也没用。
- `.sys` 若被注册成服务并加载进内核，会一直处于 mapped 状态，必须先 `stop` + `delete` 服务并等内核卸载映像。
- 全局钩子（RTSS 之类做覆盖层/注入的软件）会把 `.dll` 注入到一堆进程里；`svchost.exe` 里的那份只能等重启。

## 修复

```powershell
# 1) 先把带锁文件的父目录整体改名移出应用目录（NTFS 允许重命名含已映射 DLL 的父目录）
Move-Item 'C:\Users\Admin\AppData\Roaming\OpenRevo\plugins\mro-hud' `
          'C:\Users\Admin\AppData\Roaming\OpenRevo\_mro-hud_pending_delete'
# 应用立刻看不到插件了（plugins\ 变干净），后续慢慢处理

# 2) 停掉并删除内核驱动服务（必须提权；本机可 Start-Process -Verb RunAs 静默提权）
sc.exe stop   RTCoreMini64
sc.exe delete RTCoreMini64
sc.exe delete RTCore64      # 顺带清同名兄弟服务；未启动时报 1062 无妨

# 3) 剩下被注入的 DLL：登记「下次开机删除」
#    Python: ctypes.windll.kernel32.MoveFileExW(path, None, 4)   # MOVEFILE_DELAY_UNTIL_REBOOT
#    注意：登记后再按「旧路径」去查会查不到，换了路径要重新登记一次

# 4) 兜底：登录时整目录清掉
#    HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce
#    CleanupXxx = cmd.exe /c rmdir /s /q "C:\...\_mro-hud_pending_delete"
```

提权 worker 的可靠写法（`-Verb RunAs` 不支持重定向 stdout，日志要自己写文件）：

```powershell
Set-Content -LiteralPath "$env:TEMP\x.ps1" -Value $script -Encoding UTF8
$p = Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"$env:TEMP\x.ps1") -Verb RunAs -PassThru -WindowStyle Hidden
$p | Wait-Process -Timeout 120
```

## 验证

- `Test-Path 'C:\Users\Admin\AppData\Roaming\OpenRevo\plugins\mro-hud'` → `False`（改名后立刻为 False）
- `Get-CimInstance Win32_Service -Filter "Name='RTCoreMini64'"` → 空（服务已删）
- 重启后 `Test-Path` 那个 `_pending_delete` 目录 → `False`（`MoveFileEx` 或 `RunOnce` 生效）
- 应用 UI 复核：OpenRevo 插件页只剩 7 张自定义插件卡、页签 6 个，`MRO HUD 控制台` 消失

## 关键教训

- **「访问被拒绝」先分清是 ACL 还是 mapped 文件**：`(Get-Item $p).IsReadOnly`、`Get-Acl` 都正常却删不掉，就是后者。
- **提权 worker 的日志别写在非系统盘的项目目录**：实测写 `G:\...` 有时静默不生成文件，写 `C:\Users\<user>\AppData\Local\Temp\` 一定成功（而 `Test-Path G:\...` 在同一进程里是 True，不是盘符不可见）。
- **先改名、后清理**：改名一步就能让应用恢复干净状态，比等重启更实用；再把 `MoveFileEx + RunOnce` 当保险。
- PowerShell 里 `EnumWindows` 用 scriptblock 当回调**不会往管道输出**（PS 5.1 限制）；要枚举窗口就用 UI Automation 的 `RootElement.FindAll(Children, ProcessIdProperty)`，它还能顺带拿到 `Tauri Window` 的 `BoundingRectangle`。

## 相关

- 同机另一篇：`踩坑-宿主以管理员运行时外部进程改不了它的窗口样式-穿透要页面自己调宿主接口.md`（同一插件：宿主提权导致 `SetWindowLongW` err=5）
- 归档记录：`G:\AIrenwu\OpenRevo插件整理\01_报告\00_归档说明与变更总账.md`（第四节「删插件比装插件麻烦」）
