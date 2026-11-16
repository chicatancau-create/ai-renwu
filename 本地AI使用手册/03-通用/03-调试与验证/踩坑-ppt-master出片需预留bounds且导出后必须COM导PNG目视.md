---
title: "ppt-master 本机出片：SVG 门禁预留、原生标记 JSON 与 PowerPoint COM 取证"
date: 2026-11-04
updated: 2026-11-15
domain: common
category: 工具链/交付取证
status: verified
severity: medium
stack: [Python, SVG, PPTX, PowerPoint COM, PowerShell]
tags: [ppt-master, svg_quality_checker, data-pptx-bounds, native-table, COM-Export, flask]
---

# 问题：用 ppt-master 在本机出可编辑 PPTX 时，四个反复踩的坑

> `needs-review` 表示尚未完成验证；只有复现、定位、修复和验证都完成后，才改为 `verified`。
> 2026-11-15 本条已升级为 `verified`：同一工程又完成 10 页重排、4 次导出与逐页 COM 渲染，新增「bounds 实际文字外框」和「历史中间件清理」两项闭环。

## 一句话结论

ppt-master 的质量门是「几何 + 元数据」双重硬约束，靠肉眼估排版会反复返工；交付前必须用 PowerPoint COM 把每页导成 PNG 亲眼看一次，不能只信 `[OK]`。

## 触发条件与影响

- 项目或功能：任何用 `D:\QoderToolkit\ppt-master` 生成 `.pptx` 的任务（本轮：G:\AIrenwu\01_任务归档\2026-11-04_影视飓风账号分析）。
- 环境与版本：Windows 10.0.28000 / x64，Python 3.x（`D:\PyCharm\Python`），PowerPoint（ClickToRun）已装。
- 触发条件：手写 23 页 SVG → 跑 `svg_quality_checker.py` → 导出 → 取证。
- 影响范围：交付时间（一轮返工约 15 分钟）与「交付物是否真的渲染成预期样子」。

## 复现步骤

1. 前置条件：项目已 `init` + `import-sources`，`design_spec.md` / `spec_lock.md` 通过 `validate`。
2. 操作或命令：
   - `python <SKILL_DIR>/scripts/text_measure.py calibrate <project> --outline`
   - `python <SKILL_DIR>/scripts/svg_editor/server.py <project> --live --daemon`
   - 手写 SVG → `stamp_native_fallbacks.py <project>/svg_output --write` → `svg_quality_checker.py <project> --canonical-authoring --stage final --json`
   - `svg_to_pptx.py <project>` → PowerShell 里 `Slides.Item($i).Export($f,'PNG',1280,720)`
3. 预期结果：预览服务可启动；门禁 0 error；导出文件与 SVG 一致。
4. 实际结果：
   - 预览服务直接 `ModuleNotFoundError: No module named 'flask'` 退出。
   - 门禁连续三轮报 error：① root `<g>` 的 `data-pptx-bounds` 比文字实际外框小 5%~19%；② 原生表格 marker 报 `row_heights must match the resolved row count (expected 6 entries, header rows included)`；③ 报 `SVG-authoritative native-object marker requires data-pptx-fallback-sha256`（因为 JSON 无效导致 stamp 跳过该对象）。
   - 同一张图片在 `spec_lock.md images` 里写两行（两个页面各一行）→ 报 `appears in multiple spec_lock.md image rows; one resource must have one authoritative row`。
   - `python-pptx` 顶层遍历只数到 139 个形状、0 张图片，误判「图没进去」。

## 证据

- 门禁原文（节选）：`<text> (x=144, y=196) exceeds <g id="p14-q1"> data-pptx-bounds ... overflow horizontal 12.3% (error above 5%); ≈19.1 px per CJK char at 18px incl. headroom; ≈36 chars fit in 700 px`。
- 预览失败原文：`File "…\svg_editor\server.py", line 39, in <module> from flask import Flask … ModuleNotFoundError: No module named 'flask'`。
- 最终一轮：`Total files: 23 / Fully passed: 13 / With warnings: 10 / With errors: 0`，导出 `[POSTFLIGHT] status=passed-with-warnings quality_gate=passed slides=23`。
- 递归遍历后：`TOTAL pictures 20 textshapes 566 groups 142`，与 checker 的 `carrier_receipt.totals`（image_placements 20、text_elements 566）逐项相等。
- 留档：`G:\AIrenwu\01_任务归档\2026-11-04_影视飓风账号分析\02_证据日志\pptx_render\s01..s23.png` 与 `contact_all.jpg`。

## 根因分析

- 已确认的根因：
  1. **bounds 不是文字框而是模块区**：检查器按「baseline − 0.85×size 到 baseline + 0.35×size」量文字，再和 root group 的 `data-pptx-bounds` 比；我按视觉行距写区，纵向必然偏小，横向按 CJK 字宽估少了余量。
  2. **原生表格的 `row_heights` 含表头行**：`columns` 算一行，所以 N 行正文要写 N+1 个权重。
  3. **stamp 与 JSON 有效性耦合**：JSON 校验不过 → 该对象不被 stamp → 下一轮报「缺 sha256」，看起来像两个问题其实是一个。
  4. **一张图一行锁**：`spec_lock.md images` 以资源为键，不以页面为键；跨页复用同一文件只写一行。
  5. **python-pptx 不递归 group**：导出把每个 root `<g>` 编成组合形状，顶层遍历必然漏。
  6. 预览服务需要 flask，本机 Python 没有；规则要求「起不来就如实说」，不是静默跳过。
- 排除过的假设：不是字体缺失（SimHei/Consolas 都正常渲染）；不是图片路径问题（`../images/` 相对路径全部命中）。
- 问题归属：修改前已有（技能包既有约束）+ 本次操作方式引入（我未先算预留）。

## 最小修复

1. 画第一页前就跑 `text_measure.py calibrate --outline`，把每个角色的「每 100px 能放几个 CJK / Latin / 数字」抄进上下文；写区时按 `baseline±0.85/0.35×size` 加 24px 横向余量，宁可区大。
2. 原生表格 `row_heights` 一律写 `1 + 正文行数`；写完立刻 `stamp_native_fallbacks.py --write`，再看它报 `SVG-first=N` 是否等于标记数。
3. 锁里每个资源一行，键名带主页面号即可（如 `p01-cover-duo`），跨页复用不再加行。
4. 核验导出用递归遍历（遇 `MSO_SHAPE_TYPE.GROUP` 下钻），并把形状数与 checker 的 `carrier_receipt` 对表。
5. 交付前用 PowerPoint COM 逐页 `Export(...,'PNG')` 拼 contact sheet 亲眼看；`.ps1` 必须 `utf-8-sig` 写，否则中文路径在 PS 5.1 下乱码。

## 验证记录

- [x] 静态检查：`project_manager.py validate` → `[OK] Project structure is complete.`
- [x] 门禁：`svg_quality_checker.py --stage final` → 0 error（返工三轮）
- [x] 构建：`finalize_svg.py` → 20 images / 23 icons embedded；`svg_to_pptx.py` → 23 slides + notes
- [x] 启动或手动回归：PowerPoint COM 导出 23 张 PNG，逐页看过（封面、表格页、图表页、章节页）
- [x] 2026-11-15 回归：10 页版 final gate `10/10 fully passed`，PowerPoint COM `EXPORTED 10`，逐页 PNG 与 contact sheet 复核通过
- [x] 2026-11-15 清理回归：删除 46 个历史中间件，释放 `59.1 MB`；最新导出、脚本引用和交付件均仍存在
- [x] flask 预览（2026-11-13 补验）：用户放行后 pip 装 flask 3.1.3（`D:\PyCharm\Python`，import 通过）；原项目缺 `svg_output` 无法直接起，改用最小夹具项目 `G:\AIrenwu\02_项目代码\preview-fixture`（`svg_output\slide_01.svg`）起 `server.py --no-browser --port 8765`，`HTTP GET /` 返回 200、日志「1 slides」，预览机制端到端可用

## 2026-11-15 复验补充

1. **bounds 要按检查器报出的实际文字外框扩，不能只看名义 baseline。**
   - 现象：`svg_quality_checker.py` 报 `content (977.5, 632.7)-(1216.0, 709.6)`，容器只到 `708.0`，纵向溢出 `1.8%`。
   - 修复：把模块高度从 `88` 扩到 `92`，重跑 stamp 与 final gate 后 `10/10 fully passed`。
2. **名义 bounds 落在 720 画布内，PowerPoint 仍可能把文字下沿裁掉。**
   - 现象：14px 两行页脚的 nominal bottom 正好 720，COM 导出 PNG 中第二行仍贴底并被裁。
   - 修复：字号降到 12px、基线上移并收紧行距；二次 COM 渲染确认完整显示。
   - 结论：SVG gate 只能证明几何契约，不能替代真实 PowerPoint 渲染。
3. **历史导出件、backup 和 validation report 是主要垃圾源。**
   - 同一工程累积 16 个导出件、16 份 SVG backup、20 份 validation 文件，仅最新一轮需要保留。
   - 反查 `export_slides.ps1`、交付记录和计划任务后，删除 15 个旧导出、15 个旧 backup、16 个旧 validation 文件，释放 `59.1 MB`；最新导出、最新 backup、当前质量报告和校准文件保留。
4. **导出成功不等于交付件仍与导出原件一致。**
   - 2026-11-15 实测：交付件已由用户改为 11 页、`4,640,480` 字节，最新导出原件仍是 10 页、`4,612,778` 字节，MD5 不同。
   - 清理时绝不能拿旧导出件覆盖交付件；先比页数、大小、MD5，再决定保留哪份。

## 可复用规则

- 用 ppt-master 画 SVG 前，先跑 calibrate 拿到字符率，再按「baseline−0.85×size / +0.35×size + 24px」写 `data-pptx-bounds`；适用条件：1280×720 且有中文正文。例外：纯装饰区。
- 原生 chart/table 标记写完必须 stamp，且 `row_heights` 含表头行；适用条件：`Native-ready=yes` 的对象。
- 声称「导出成功」前必须做一次递归形状计数 + COM 导 PNG 目视；不适用：只交付 SVG 预览的任务。

## 适用范围与不适用范围

- 适用：ppt-master 默认生成路线（Default Generate）、flat 结构、含原生图表/表格与图片的中文 deck。
- 不适用：Edit Native PPTX 的 round-trip 路线（那里 bounds 由还原器决定）；`structured` 模板路线（另有 slot 约束）。

## 剩余风险

- 18 条 `introduced` 级 advisory 警告（多为原生导出对齐细节与段落行合并提示）未逐条消除，只影响 `--native-charts-and-tables` 那条未被使用的导出分支。
- 未测 LibreOffice / WPS 打开同一文件的排版差异；未测打印（暗底 + chunk-filled 实心态在打印下应可，未验证）。
- PowerPoint COM 路线已在同一工程的多轮 10 页导出中复现，但仍属于本机 Microsoft Office 版本结论；其他 Office 版本需重新实测。
- flask 缺失导致预览不可用：**已修**（2026-11-13 用户放行「能修的就修」后 pip 装 flask 3.1.3，最小夹具项目启动预览 HTTP 200 验证）。原「不擅自装依赖」约束经用户明确放行解除。

## 关联

- 相关记录：[[踩坑-沙箱只放行工作区致写E盘被拒且write会抹掉源码BOM]]（同属「写盘与编码」类）
- 相关分类：03-通用 / 交付取证
- 相关代码、命令或文档：`D:\QoderToolkit\ppt-master\references\executor-base.md` §3（bounds 与 width estimation）、`references\native-data-interface.md` §2、`G:\AIrenwu\01_任务归档\2026-11-04_影视飓风账号分析\03_工具脚本\export_slides.ps1`
