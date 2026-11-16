---
title: "Excel 区域 CopyPicture 贴进 Chart 再 Export 得到空白 PNG；改用剪贴板 GetImage 或 PowerPoint Slide.Export"
date: 2026-11-03
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [PowerShell 5.1, Excel COM, PowerPoint COM, python-pptx, System.Drawing]
tags: [排版取证, Excel, PowerPoint, 渲染出图, COM]
---

# 问题：脚本把 xlsx 渲染成 PNG，Chart-Paste-Export 路径静默出空白图；PS 5.1 还报找不到 System.Drawing 类型

## 一句话结论

本机 Excel COM 的 `Range.CopyPicture` → 贴进 `ChartObjects` 新建图表 → `Chart.Export` 会**不报错地导出全白 PNG**；
可靠路径有两条：① Excel 可见 + `CopyPicture` 后用 `[System.Windows.Forms.Clipboard]::GetImage()` 存图；
② 用 python-pptx 把同一张表做成幻灯片，PowerPoint COM `Slide.Export($png,'PNG',宽,高)` 出图（可指定像素，最稳）。
另：PS 5.1 脚本里用 `[System.Drawing.Image]` / `[System.Windows.Forms.Clipboard]` 前必须 `Add-Type -AssemblyName`，否则报类型找不到。

## 触发条件与影响

- 项目或功能：脚本生成 xlsx 交付时要附一张表格截图（2026-11-03「认识短视频平台」作业，四平台六列对比表）。
- 环境与版本：Windows PowerShell 5.1；Office16（`C:\Program Files\Microsoft Office\Root\Office16\` 的 EXCEL/POWERPNT）；
  bundled Python（openpyxl 3.1.5、python-pptx 1.0.2、Pillow 12.3.0）。**本机无 LibreOffice / ImageMagick / poppler / Ghostscript**，出图只能走 Office COM。
- 触发条件：用「区域复制为图片 → 粘贴到空白图表 → 图表导出」这条常见网文路径渲染表格。
- 影响范围：导出"成功"（无异常、文件存在）但图是空白，若不肉眼检查会把空白图当交付物。

## 复现步骤

1. 前置条件：openpyxl 写好一张含多行中文的表；Excel COM 打开。
2. 操作（失败路径，export_png.ps1）：
   `$rng.CopyPicture(1,2)`（xlScreen, xlBitmap）→ `$ws.ChartObjects().Add(0,0,1500,780)` → `$chart.Chart.Paste()` → `$chart.Chart.Export($png)`。
3. 预期结果：得到表格截图。
4. 实际结果：**2500x1300、P 模式、3072 字节的全白 PNG**，全程无报错。
   同脚本另一处独立报错：`Unable to find type [System.Drawing.Image].`（export_png.ps1:38）——PS 5.1 默认没加载 System.Drawing 程序集。

## 证据

- 空白图实测：3072 字节 / 2500x1300 / P 模式（正常表格截图应为几十~几百 KB）。
- 剪贴板路径实测：Excel `Visible=$true` + `$rng.CopyPicture(1,2)` + `Start-Sleep -Milliseconds 600` +
  `[System.Windows.Forms.Clipboard]::GetImage().Save($png)` → **1579x694 PNG，肉眼无裁字**。
- PPT 路径实测：python-pptx 建表格幻灯片 → `Presentations.Open($pptx,$true,$false,$false)` →
  `$pres.Slides.Item(1).Export($png,'PNG',2560,1440)` → **2560x1440、179591 字节，肉眼干净**。
- 证据原件说明：原任务目录 `G:\AIrenwu\2026-11-03_认识短视频平台作业\` 已于 2026-11-15 按用户要求整体删除，
  原始 PNG/脚本不存；本记录保留关键数值与报错原文，上面三条路径均可按步骤重跑复现。

## 根因分析

- 已确认（现象级）：Chart-Paste-Export 路径在本机静默出空白；两条替代路径均出正确图，多轮渲染复核一致。
- 未深究：空白的底层机制（怀疑 `Chart.Paste` 与剪贴板/图表渲染面的时序问题）**没有做机制级定位**，
  结论按「该路径在本机不可靠」记录，不写成已证实的根因。
- `Unable to find type [System.Drawing.Image].` 的根因已确认：PS 5.1 不预加载 System.Drawing / System.Windows.Forms，需显式 `Add-Type -AssemblyName`。
- 问题归属：环境或依赖（本机 Office COM 行为 + PS 5.1 程序集加载），不是表格数据问题。

## 最小修复

```powershell
# 脚本头部（PS 5.1 必须）
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# 路径①：剪贴板取图（Excel 必须 Visible）
$excel.Visible = $true
$rng.CopyPicture(1,2)
Start-Sleep -Milliseconds 600
[System.Windows.Forms.Clipboard]::GetImage().Save($png)

# 路径②（首选）：python-pptx 表格幻灯片 + PowerPoint 导出，可指定像素
$pres = $ppt.Presentations.Open($pptx, $true, $false, $false)
$pres.Slides.Item(1).Export($png, 'PNG', 2560, 1440)
```

## 验证记录

- [x] 失败路径复现：Chart-Paste-Export 出 3072B 空白图（反例实测）。
- [x] 修复路径①：剪贴板法出 1579x694 PNG，肉眼检查无裁字。
- [x] 修复路径②：PPT 法出 2560x1440 PNG（179591B），多轮迭代每轮肉眼签字。
- [x] Add-Type 修复后类型报错消失。
- [ ] 空白机制级根因：未做（不影响「换路径」这一修复决策）。

## 可复用规则

- 本机把 Office 表格渲染成 PNG：**不走 Chart-Paste-Export**；首选 PPT `Slide.Export`，次选 Excel 剪贴板 `GetImage`。
- 出图后**必须查字节数 + 打开肉眼**：几 KB 的"导出成功"就是空白图；"没报错"不等于"有内容"。
- PS 5.1 脚本用到 `System.Drawing` / `System.Windows.Forms` 类型，头部先 `Add-Type -AssemblyName`。
- 中文 stdout 经 pwsh 回显会 GBK 乱码：取证日志用 Python 写 UTF-8 文件再 read，别靠控制台回显判内容。

## 适用范围与不适用范围

- 适用：本机 Office16 COM + PS 5.1 的表格/幻灯片出图；无 LibreOffice 等替代渲染器的环境。
- 不适用：已装 LibreOffice/headless 浏览器的机器（可直接转 PDF/截图）；WPS 的 COM 行为未实测。

## 剩余风险

- 剪贴板路径依赖 Excel 可见且剪贴板不被其他程序抢占（600ms 等待是经验值，极端情况仍可能取空）。
- PPT 路径依赖本机字体（微软雅黑）；换字体需重测排版。
- Chart 路径空白的机制未定位，不排除特定条件下可用——但没必要再赌。

## 关联

- 相关记录：[[踩坑-openpyxl写的xlsx在Excel里行高被裁字]]（行高要显式写死）、[[踩坑-Office不守中文禁则且PPT二次折行切词需预断行]]（断行位置）、[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]、[[踩坑-GetContent默认按代码页解码致UTF8中文回显乱码]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
