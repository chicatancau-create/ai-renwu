---
title: "Windows 桌面取证：托盘图标在独立溢出窗口、截图要先设 DPI-aware、UIA 静态成员写法"
date: 2026-10-14
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [Windows, UIAutomation, PowerShell, C++, Qt6]
tags: [桌面取证, 托盘, DPI, UIAutomation, PowerShell]
---

# 问题：想证明"托盘图标真的注册上了"，肉眼截图和常规枚举都失败

## 一句话结论

三条独立结论：① Win11 的隐藏托盘项**不在 `Shell_TrayWnd` 子树里**，而在独立的顶层窗口
`TopLevelWindowForOverflowXamlIsland`，必须先 Invoke 展开箭头才看得到；② 用 `Graphics.CopyFromScreen`
做取证**必须先 `SetProcessDPIAware()`**，否则量到的几何是缩放后的假数；③ 24px 托盘图标**不具备肉眼可辨性**，
判据要用 UIA 的 Name（即 tooltip）而不是像素比对。

## 触发条件与影响

- 项目或功能：验证自研托盘应用真的把图标注册进了资源管理器。
- 环境与版本：Win11（10.0.28000）+ Windows PowerShell 5.1 + 2560×1600 @ 125% 缩放面板。
- 触发条件：只走 `Shell_TrayWnd` 后代枚举 / 直接截任务栏肉眼看。
- 影响范围：会得出"图标没注册上"的**假阴性**结论。

## 复现步骤

1. 前置条件：一个只驻留托盘、无主窗口的 GUI 进程在跑。
2. 操作或命令：
   - A：UIA 从 `Shell_TrayWnd` 走 ControlView 全子树，找自己的 tooltip。
   - B：`GetWindowRect(Shell_TrayWnd)` 反推展开箭头坐标去点。
   - C：不设 DPI-aware 直接 `CopyFromScreen`，对比屏幕真实分辨率。
3. 预期结果：A 能找到；B 能点开溢出区；C 拿到真实像素。
4. 实际结果：A 找不到（假阴性）；B 两次点位偏差 20px 都没点开；C 拿到 2048×1280 而非 2560×1600。

## 证据

A 只走 `Shell_TrayWnd` 时，可见区 12 个按钮里没有自己：

```
VISIBLE_TRAY_BUTTONS=12
  visible: SystemTray.NormalButton|显示隐藏的图标
  visible: SystemTray.NormalButton|CC Switch
  ... （全是系统项，没有本应用）
```

改为「UIA Invoke 展开箭头 → 枚举所有顶层窗口的后代」后命中：

```
WINDOW class=TopLevelWindowForOverflowXamlIsland buttons=11
    SystemTray.NormalButton|<被测应用> 学习版        ← 本次要证明注册的那个
    SystemTray.NormalButton|<某第三方截图工具> v3.5.5 ← 同栏并列的既有项
```

C 的对照：同一个面板，Qt 报 `logicalGeometry=2048x1280 / devicePixelRatio=1.25`，
`CopyFromScreen` 在调用 `SetProcessDPIAware()` 后输出 `SCREEN=2560x1600`，不调用则输出 2048×1280。

## 根因分析

- 已确认的根因：
  - Win11 把通知区域拆进 XAML 岛，溢出区是**独立顶层窗口**，不是任务栏的子元素。
  - 非 DPI-aware 进程拿到的坐标空间是虚拟化的（÷1.25），截图与点击都会偏。
  - 托盘图标渲染尺寸 24px，人眼无法区分自绘角标与别的深色图标。
- 排除过的假设：不是图标没注册（`Shell_NotifyIcon` 确实成功，UIA 能查到名字）；
  不是 Qt 的 `showMessage` 失败导致没注册（气泡与注册是两件事，见「剩余风险」）。
- 问题归属：修改前已有（对 Win11 托盘架构的既有认知偏差）。

## 最小修复

```powershell
# 1) 取证点位/截图：先声明 DPI 感知
[Win32.U32]::SetProcessDPIAware()

# 2) 找托盘项：展开箭头用 UIA Invoke，不要猜坐标；再遍历所有顶层窗口
$chevron = $tray.FindFirst([TreeScope]::Descendants, (New-Object PropertyCondition(
    [AutomationElement]::ClassNameProperty, 'SystemTray.NormalButton')))
$chevron.GetCurrentPattern([InvokePattern]::Pattern).Invoke()

# 3) 判据用 Name（tooltip），不用像素比对
```

## 验证记录

- [x] 手动回归：同一脚本连续两次输出 `VISIBLE_TRAY_BUTTONS=12` + 溢出区命中本应用。
- [x] 反向对照：修好单实例守卫前，任务栏按钮列表里会多出一条 `<被测应用>.exe - 1 个运行窗口`；修好后消失。
- [ ] 自动化测试：未做（取证脚本本身即工具）。

## 可复用规则

**证明"托盘项存在"只认 UIA 的 `Name`，且必须遍历所有顶层窗口（含 `TopLevelWindowForOverflowXamlIsland`），
不要只走 `Shell_TrayWnd`；任何桌面几何取证（截图/点击/裁剪）第一步都是 `SetProcessDPIAware()`。**
判据：截图尺寸 ≠ 面板物理分辨率，或点击坐标系统性偏差一个缩放比 → 就是 DPI-aware 没设。

## 适用范围与不适用范围

- 适用：Win11 通知区域取证、桌面应用的自动化验收、任何需要真实像素几何的测量。
- 不适用：Win10 经典 `TrayNotifyWnd` + `ToolbarWindow32` 结构（那里可以直接枚举）；
  PowerShell 7（`Add-Type`/类型解析行为不同，本记录未验证）。

## 剩余风险

- **PowerShell 5.1 的两个语法坑**（同一轮踩到，已确认但归入关联记录）：
  `$TRUE = ...` 会撞上保留的 `$true` 报 `VariableNotWritable`；
  用类型变量取静态属性 `$AE::ClassNameProperty` 返回 null，必须写全名 `[System.Windows.Automation.AutomationElement]::ClassNameProperty`。
- Qt 的 `QSystemTrayIcon::showMessage` 在 Win11 上**未弹出气泡**，是配置问题还是平台行为**未证实**；
  因此气泡不能当验收手段，本记录改用 UIA。

## 关联

- 相关记录：[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]、[[规则-Windows新窗口默认居中只能常驻监视器]]（DPI 相关）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：来源工程已于 2026-10-15 删除，无可跳转路径（结论仍由当时的自产证据支撑）；脚本骨架见上面「最小修复」的三段代码。
