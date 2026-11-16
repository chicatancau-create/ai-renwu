---
title: "任务栏图标变成白纸页：系统按 AUMID 取的是「开始菜单快捷方式」的图标，而它指向了已卸载的旧路径"
date: 2026-11-15
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Windows 11, 任务栏, AUMID, .lnk, UI Automation]
tags: [图标变白, AUMID, IconLocation, 开始菜单快捷方式, SHChangeNotify]
---

# 问题：程序本身图标正常，任务栏上却是一个白色文件页

## 一句话结论

Windows 11 任务栏对「已固定但未运行」的按钮，是按 **AUMID（AppUserModelID）** 去找**携带同一 AUMID 的快捷方式**，
用那个快捷方式的 `IconLocation` 画图标。本机 `Motrix` 的开始菜单快捷方式 `IconLocation` 指向
`C:\Users\Admin\AppData\Local\Programs\Motrix\Motrix.exe,0`——**这个目录早已不存在**（程序现在装在
`D:\_整理\01-软件\04-网络与下载\Motrix\Motrix.exe`），于是退化成系统的「未知文件」白纸页。
**把那个快捷方式的 `IconLocation` 改回真实 exe，任务栏立刻恢复，不需要重启资源管理器。**

## 触发条件与影响

- 触发条件：**程序被移动/重装到别的目录，但开始菜单快捷方式没跟着更新**；且该快捷方式带 AUMID。
- 影响：任务栏/开始菜单图标变白纸页，看起来像「图标丢了」，很容易误判成「程序没设图标」或「Windows 图标缓存坏了」。
- 桌面快捷方式往往是正常的（它没有 AUMID、图标指向真身），这个「桌面正常、任务栏白」的错位是最强线索。

## 三步定位（全部实测判据）

```powershell
# 1. 任务栏那个按钮到底是谁 —— 用 UIA 读它的 AutomationId
#    形如 "Appid: app.motrix.native"，这就是 AUMID
#    （顺带能拿到 BoundingRectangle，与用户红框对得上才算确认）

# 2. 窗口/类图标正常吗？正常就说明程序本身没问题
#    GetClassLongPtr(hwnd, -14) = GCLP_HICON，取出后存 PNG 肉眼看
#    WM_GETICON(ICON_BIG/ICON_SMALL/ICON_SMALL2, msg 0x007F) 全返回 0 是常见情况，不代表没图标

# 3. 找携带同一 AUMID 的快捷方式，看它的 IconLocation
$sh = New-Object -ComObject Shell.Application
$lnk = $sh.NameSpace('C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs')
$item = $lnk.ParseName('Motrix.lnk')
$item.ExtendedProperty('System.AppUserModel.ID')   # -> app.motrix.native
$item.ExtendedProperty('System.Link.TargetParsingPath')
```

本机取证结果对照：

| 对象 | 图标来源 | 结果 |
|---|---|---|
| exe 本身（`ExtractAssociatedIcon` / `SHGetFileInfo`） | 内嵌资源 | 正常（紫色） |
| 窗口类图标（`GCLP_HICON`） | 进程内 | 正常（紫色） |
| 桌面 `Motrix.lnk`（无 AUMID，指向真身） | exe | 正常 |
| **开始菜单 `Motrix.lnk`（带 AUMID）** | 已不存在的旧路径 | **白纸页 ← 就是它** |

## 根因分析

- 任务栏按 AUMID 归组，要画图标时优先用「同一 AUMID 的快捷方式」的 `IconLocation`，而不是进程的窗口图标。
- 该 `IconLocation` 是**绝对路径 + 图标索引**，程序换目录后就是一个坏引用；系统不会回退到 exe 内嵌图标，而是给通用图标。
- 这也解释了为什么 `WM_GETICON` 返回 0、类图标却正常：窗口图标从头到尾没参与这次绘制。

## 最小修复

```powershell
$p = 'C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Motrix.lnk'
Copy-Item $p 'C:\Users\Admin\.dsh\tools\motrix-lnk-backup\Motrix.lnk.bak-20261115-033626'
$w = New-Object -ComObject WScript.Shell
$s = $w.CreateShortcut($p)
$s.IconLocation = 'D:\_整理\01-软件\04-网络与下载\Motrix\Motrix.exe,0'
$s.Save()
# 通知 shell 图标已变
# SHChangeNotify(SHCNE_ASSOCCHANGED=0x08000000, SHCNF_IDLIST=0, 0, 0)
```

两条必须注意的细节：

1. **备份文件不能留在「开始菜单\Programs」目录里**——`.lnk` 会被当成一个开始菜单条目显示出来。备份放别处。
2. 改完**不用重启 explorer.exe**：发一次 `SHChangeNotify` 即可，实测立即生效。

## 验证记录

- 修复前：对开始菜单 lnk 跑 `SHGetFileInfo`，32×32、主色 `250,250,250`（白纸页）。
- 修复后：同一调用得到真实图标（`iIcon=50`，与桌面快捷方式一致）。
- 屏幕实拍：`SetProcessDPIAware()` 后 `CopyFromScreen` 抓全屏、裁任务栏 `x1490 y1525 w160 h75` 放大 6 倍肉眼确认已变紫色图标；**全程没重启资源管理器**。

## 可复用规则

- **「桌面图标正常、任务栏图标白」→ 先查带 AUMID 的开始菜单快捷方式，不要先去重建图标缓存。**
- 程序搬家后，凡是 `.lnk` 里的 `IconLocation`/`TargetPath` 用绝对路径的都会坏；搬家后应批量扫一遍开始菜单。
- 图标类问题先用 `SHGetFileInfo`/`ExtractAssociatedIcon` 把**同一对象的三种来源**（exe 内嵌 / 窗口类 / 快捷方式）分别验一遍，直接看谁返回了白图，比猜缓存快得多。
- 抓屏取证前先 `SetProcessDPIAware()`，否则拿到的是缩放后的坐标，裁出来的位置会偏（参见 [[03-通用/03-调试与验证/踩坑-Win11托盘图标在独立溢出窗口且取证须先设DPI-aware|Win11 托盘图标在独立溢出窗口，取证须先设 DPI-aware]]）.

## 适用范围与不适用范围

- 适用：固定到任务栏的桌面程序，图标异常但程序本身正常。
- 不适用：任务栏图标整体大量变白（那是图标缓存/`IconCache.db` 问题）；UWP/Store 应用（图标来自包清单，不是 `.lnk`）；托盘图标（是另一套，见上条关联记录）。

## 剩余风险

- `GetApplicationUserModelId` 在 `shell32.dll` **没有导出**，想直接读 AUMID 会 `EntryPointNotFoundException`；改从 UIA 的 `AutomationId` 拿，或用 `Shell.Application` 的 `ExtendedProperty('System.AppUserModel.ID')`。
- 如果程序自己重装/自更新时重写快捷方式，`IconLocation` 可能再次被写成旧路径；搬到新目录后隔一段时间复查一次任务栏。

## 关联

- [[03-通用/03-调试与验证/踩坑-Win11托盘图标在独立溢出窗口且取证须先设DPI-aware|Win11 托盘图标在独立溢出窗口，取证须先设 DPI-aware]]
- [[03-通用/03-调试与验证/踩坑-Win11改默认程序无效是OpenWithProgids压制默认ProgId|Win11 双击还是弹「打开方式」：OpenWithProgids 压制默认 ProgId]]
