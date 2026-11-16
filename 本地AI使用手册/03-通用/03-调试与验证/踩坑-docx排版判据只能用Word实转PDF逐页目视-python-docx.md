---
title: "docx 排版只能用 Word 实转 PDF 逐页目视；python-docx 的四个静默坑"
date: 2026-11-15
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [python-docx, Word COM, PyMuPDF, PIL, Obsidian]
tags: [docx排版, Word自动化, 目视取证, 图片清理, 样式映射]
---

# 问题：python-docx 生成的 Word 文档「结构对」不等于「排版对」，两处问题只有把 PDF 逐页渲染出来才看得见

> 这是「docx 排版必须用 Word 实测渲染」的第二次实例。这次抓到的是**截图底部大片空白**和**各图数据态互相矛盾**——两者在 XML 层面完全看不出来。

## 一句话结论

判 docx 排版只有一条路：**Word COM 转 PDF → PyMuPDF 逐页出 PNG → 逐页目视**；python-docx 侧另有四个会静默丢东西的坑（body 遍历、删图留 rel、代码块软换行、改格丢 rPr），照下面的对应关系写即可绕过。

## 触发条件与影响

- 项目或功能：把课程《实训案例题库》HTML 的视觉语言套进官方「集中实训情况登记表」的单个大表格里（四节正文 + 3 张嵌套表 + 5 张截图 + 代码块）
- 环境与版本：Python 3.14 + python-docx、Microsoft Word（C2R）COM、PyMuPDF、Pillow 12.3
- 影响范围：交付物观感；以及删图不净导致包体虚胖

## 四个静默坑（都已实测）

1. **遍历 body**：`Document` 对象没有 `iterchildren`，`hasattr(d,'body')` 又为真，直接 `walk(d)` 会 `AttributeError`。要用 `d.element.body.iterchildren()`，包装 `Table/Paragraph` 时传 `parent=None`。
2. **删段落里的图片不会清 rel**：删掉含 `<w:drawing>` 的 `<w:p>` 后，包里的 `word/media/image1.png` 仍在。要额外清 orphan rel，实测 media 从 8 项降到 5 项、`document.xml` 的 blip 数从 8 降到 5 才算真删净。
3. **代码块不能靠自动换行**：`<pre>` 式缩进必须用 `run.add_break()` 逐行硬换行，否则 Word 会把整段折成一坨，缩进全丢。
4. **改表格单元格的文字会丢字体**：封面「题目」格只换 `text` 会把原 run 的 `rPr`（宋体 12pt、`w:b w:val="0"`）丢掉。要读原 `rPr` 复制过去，改完再逐字节比对确认一致。

## HTML 设计 token → Word 的对应关系（可实现的）

| HTML 里的东西 | Word 里的落法 |
| --- | --- |
| `h4::before{content:"▍"}` 蓝色分节标题 | `▍` 单独一个 run 上色 `3B6FD4`，题面 run 上 `1F3A5F` |
| `th{background:#eaf0fa}` 表头 | **单元格级 `w:shd`**，不要用表样式（嵌套表里表样式不生效） |
| `tbody tr:nth-child(even)` 斑马纹 | 逐行按奇偶设 `w:shd` |
| `pre{border-left:3px solid}` 代码块 | 段落底纹 `F7F9FC` + 左边框 `3B6FD4` 3pt + 左右缩进 0.3cm + 单倍行距 |
| 正文首行缩进 2 字符 | `firstLineChars=200`（**不要用绝对 pt**，字体一换就错位） |
| 嵌套表列宽 | `tblLayout=fixed`，否则 Word 会按内容自动挤列 |
| 圆角卡片 / box-shadow / pill 徽章 / `:hover` | **Word 无对应物**，只能降级为浅底 + 左边框段落，或干脆只留文字 |

## 只有目视才抓到的两件事

- **截图底部大片空白**：`deviceScaleFactor=2` 下视口 2560×1800，而页面内容只到 1360px，Word 里图片下方是一整块浅蓝空底，15.5cm 宽时尤其明显。
  修法：逐行判「整行是否等于页底色」从底部往上裁；**扫描时要排除右侧 44px**，否则 headless 的竖向滚动条会被当成内容，裁不动（实测第一版裁完仍是 2560×1800）。
  竖版窄屏图按**高度上限**缩放并留 0.5cm 余量，防「图 + 图注」跨页。
- **各图数据态互相矛盾**：截图直接取验收脚本跑完的产物，于是图 2 是 4 行习惯、图 4 显示「习惯总数 3 个」——同一轮里先加后删。XML 层面完全正常，只有逐页看图才发现。
  修法：拍图单独一趟，跑在干净种子态，全程不做增删改。

## 验证记录

- [x] Word COM 转 PDF：`PAGES=9 CHARS=4970`，零报错（PowerShell 脚本须 **utf-8-sig** 写盘，无 BOM 会被 ANSI 解码打乱中文路径）
- [x] PyMuPDF 逐页出 PNG（910×1287 @110dpi）并逐页目视，第 2 轮重拍后数据态一致
- [x] python-docx 重开自检：简况单元格 41 段、3 张嵌套表（6×2 / 7×4 / 9×2）、`inline_shapes`=5、包内 media=5、markdown 残留 0
- [x] 版心核对：图片 15.50cm / 9.01cm ≤ 17.0cm 可用宽度；嵌套表实测 9637 dxa = 16.996cm
- [x] 原件未被污染：模板 `.docx` 字节数与 mtime 不变，只新增一个输出文件

## 可复用动作

1. 生成完先跑一遍**结构自检**（段落数 / 嵌套表数 / `inline_shapes` / 包内 media / 封面格 rPr 比对），再进 PDF。
2. 判排版只认 Word COM 转 PDF + 逐页 PNG 目视；不要用字体度量估分页（WPS 与 Word 页数还会不一致）。
3. 删旧图要同时清 rel，并核对包内 media 数量。
4. 往官方表格模板里写内容，**先 dump 出每个段落的索引与作用**，按索引删区间、在锚点段之间插新内容，别整表重建（会丢模板自带的表头行与签名行）。
5. 截图与验收分趟跑；裁图排除滚动条边缘带。

## 适用范围与不适用范围

- 适用：python-docx 生成/改写官方表格型文档、把 Web 设计语言移植进 Word、docx 交付验收
- 不适用：纯文本导出（直接写 md/txt 无需这套）；需要精确分页控制的正式出版物（Word 的流式排版本身不可控，应换 LaTeX/Pandoc）

## 剩余风险

- 缺宋体/Consolas 的西文 Word 环境打开会字体回退，本机中文 Word 未复现
- Word 打开输出文件会更新其 mtime（字节不变），若作业系统按 mtime 判重需注意
- 嵌套表行高靠 Word 自动撑开（未设 `trHeight`），极端缩放打印下长行会变高但不被裁（PDF 全文已证）
- 「HTML 圆角/阴影无法还原」是 Word 的能力边界，不是实现缺陷；若老师要求像素级一致，只能改为交 HTML 或整页贴图

## 关联

- 相关记录：`03-通用/03-调试与验证/踩坑-openpyxl写的xlsx在Excel里行高被裁字.md`（同一族：Office 组件的排版判据只能由真实 Office 给出）
- 相关记录：`01-前端/09-测试与质量/踩坑-自写CDP探针的七种假阳性-真浏览器取证.md`（截图数据态矛盾那条）
- 相关记录：`99-收件箱/待验证-WordCOM打不开H盘doc复制到本地后成功.md`
- 相关代码、命令或文档：生成脚本原在 `C:\tmp\vuedoc\work\build.py`，**已随会话清理删除**（其依赖的官方模板原件也已不在本机）；裁图与逐页渲染逻辑见本文「只有目视才抓到的两件事」，按需用 PIL + PyMuPDF 重建
