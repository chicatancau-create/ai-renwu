---
title: "openpyxl 生成的 xlsx 在 Excel 里行高不足被裁字"
date: 2026-10-10
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [Python, openpyxl, Excel COM, PowerShell]
tags: [排版取证, Excel, 行高]
---

# 问题：openpyxl 写的多行单元格，Excel 打开/导出 PDF 时行高不够，文字被裁并跨行重叠

## 一句话结论

openpyxl 不写行高时 Excel 不会可靠地按换行内容撑高；COM 里 `Cells.WrapText` + `Rows.AutoFit()` 跑两遍也修不干净。
**要按列宽自己估算可视行数、把行高显式写死**，并且必须导 PDF 出图肉眼看，不能只信"数据对了"。

## 触发条件与影响

- 项目或功能：脚本生成含长中文文本、单元格内 `\n` 多行的报表类 xlsx（2026-10-09 违纪情况表）。
- 环境与版本：本机 Python + openpyxl 3.1.5 + 桌面版 Excel（COM 自动化）。
- 触发条件：单元格文本按列宽换行后超过 1 行，且未显式设置 `row_dimensions[r].height`。
- 影响范围：交付表格打印/导 PDF 时文字被裁、行间重叠，数据本身没错但不可交付。

## 复现步骤

1. 前置条件：一列宽 44、单元格里放 15 行 `\n` 文本 + 若干条超长句。
2. 操作或命令：openpyxl 保存 → Excel COM `ExportAsFixedFormat` 导 PDF → 出图。
3. 预期结果：每行完整显示。
4. 实际结果：行高只够 1–2 行，超出部分被裁，且与相邻行的文字叠在一起。

## 证据

- `G:\AIrenwu\01_任务归档\2026-10-09_违纪表格式改造\02_证据日志\`：修之前 `A-第1页.png` 可见张钧/彭龙翔两行重叠、刘志华末行被裁；
  修之后 `最终版-第1~3页.png` 无裁字无重叠。
- 试过无效的路线：COM 内先设 `WrapText` 存盘、重开再 `Rows.AutoFit()` + `Cells.EntireRow.AutoFit()`，导出后仍是同样两处裁字。

## 根因分析

- 已确认的根因：xlsx 的行高是显式存储的属性；openpyxl 不计算文本换行后的高度，Excel 的 AutoFit 对
  "单元格内多行 + 长句再换行"的混合内容算短，导出分页时按短行高裁切。
- 排除过的假设：不是列宽不够（横向铺 15 列那版是另一回事）；不是 `fitToWidth` 缩放导致（关掉缩放同样裁）。
- 问题归属：本次修改引入（脚本生成侧）。

## 最小修复

生成阶段自己算行高，不依赖 Excel：

```python
def weighted(s):                      # CJK 按 2 个宽度单位算
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in s)

lines = 1
for letter, w in colw.items():        # colw: {'A':17,'E':52,...}
    v = ws[f"{letter}{r}"].value
    if v is None: continue
    n = sum(max(1, math.ceil(weighted(seg) / max(6.0, w - 1)))
            for seg in str(v).split("\n"))
    lines = max(lines, n)
ws.row_dimensions[r].height = 14.2 * lines + 5
```

原则：**宁可留白，不可裁字**。行高要在 `frame()`/页脚之前设置，否则会把合并的脚注行也算成超高行。

## 验证记录

- [x] 静态核对：`verify.py` 回读产物 10 项断言全 PASS（行数、逐字段一致、分组连续、排序）。
- [x] 渲染取证：Excel COM 导 PDF → PyMuPDF 出 PNG → 逐页肉眼确认无裁字无重叠。
- [ ] 单元/集成测试：不适用（一次性脚本）。
- [x] 构建/产物：`04_产物\违纪情况表_最终版.xlsx` A4 横向 3 页。
- [x] 手动回归：页 1 与末页（含脚注）均检查。

## 可复用规则

凡是脚本生成 xlsx/docx 并要交付：**排版结论只能用真实渲染器出图来签**（Excel/Word COM 导 PDF 或 headless 浏览器截图），
"数据核对全绿"不等于"排版没问题"。多行内容要显式写行高，别指望 AutoFit。

## 适用范围与不适用范围

- 适用：openpyxl / xlsxwriter 等不计算行高的写库；含 `\n` 或超长文本的报表。
- 不适用：纯数值窄表；由 Excel 交互编辑后再导出的场景。

## 剩余风险

行高是按字宽估算的，换字体（非宋体）、更宽的行内标点密度、或 WPS 打开时仍可能有 1–2 行误差；
WPS 与 Excel 的分页行为未分别实测。

## 关联

- 相关记录：[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]
- 相关记录：[[踩坑-Office不守中文禁则且PPT二次折行切词需预断行]]（断行位置与禁则，与本记录的行高问题互补）
- 相关记录：[[踩坑-Excel区域贴Chart导出空白PNG改用剪贴板或PPT导出]]（渲染出图的可靠路径）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：`G:\AIrenwu\01_任务归档\2026-10-09_违纪表格式改造\03_工具脚本\rebuild.py` 的 `autoheight()`
