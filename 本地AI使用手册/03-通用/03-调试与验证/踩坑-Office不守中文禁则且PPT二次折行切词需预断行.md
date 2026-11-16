---
title: "Excel/PowerPoint 自动换行不守中文禁则，PPT 还会二次折行切碎拉丁词；须 Pillow 度量预断行 + word_wrap=False"
date: 2026-11-03
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [python-pptx, openpyxl, Pillow, PowerPoint COM, Excel COM]
tags: [排版取证, 禁则, 换行, CJK, 表格]
---

# 问题：中文标点跑到行首、KOC/DOU+/18–35 被折行切碎——Office 的自动换行不可信，交付表格要自己预断行

## 一句话结论

Excel/PowerPoint 的单元格自动换行**不做中文禁则处理**（逗号句号会出现在行首），PowerPoint 还会按自己的度量**二次折行**，
把 `KOC` 切成 `KO/C`、`DOU+` 切成 `D/OU+`、`18–35` 切成 `18–3/5`。
可靠做法：用 Pillow 字体度量自己算断行（原子 token + 禁则集合），写入显式 `\n`，PPT 单元格设 `text_frame.word_wrap=False`，
留 0.93 安全边距，最后真实渲染出图肉眼签字。

## 触发条件与影响

- 项目或功能：脚本生成含大量中文短语 + 拉丁缩写的对比表（2026-11-03「认识短视频平台」作业），xlsx 与 PNG 双交付。
- 环境与版本：bundled Python（python-pptx 1.0.2、openpyxl 3.1.5、Pillow 12.3.0）；Office16 COM 出图；字体微软雅黑（`C:\Windows\Fonts\msyh.ttc` / `msyhbd.ttc`）。
- 触发条件：单元格文本交给 Office 自动换行，且内容混排中文标点与拉丁词/数字区间。
- 影响范围：标点行首、词被切碎，观感不合格；数据本身没错但不可交付。

## 复现步骤

1. 前置条件：python-pptx 表格幻灯片，单元格放「算法推荐 + DOU+ 加热、18–35 岁、KOC 种草」这类混排文本，列宽收窄到需要换行。
2. 操作：PowerPoint COM `Slide.Export` 出 PNG。
3. 预期结果：按词/标点规则换行。
4. 实际结果：`，`、`。` 出现在行首；`KOC`→`KO/C`、`DOU+`→`D/OU+`、`18–35`→`18–3/5`（PPT 按自己的度量又折了一次）。

## 证据

- 多轮真实渲染 PNG 肉眼检查：首版可见标点行首与切词；修复后终版 2560x1440（179591B）干净，xlsx 剪贴板渲染 1579x694 无裁字。
- 断行不变量测试（test_wrap.py）：行首禁则 / 行尾开括号 / 多字符 token 完整 / 行宽不超 / 字符不丢，五项全过 failures=0。
- 修复过程中实测过的 bug：第一版禁则「回拉」实现会丢字符（测试报 LOST-CHARS），重写为 token 级 wrap 后消失。
- 证据原件说明：原任务目录 `G:\AIrenwu\2026-11-03_认识短视频平台作业\` 已于 2026-11-15 按用户要求整体删除；
  本记录保留关键数值与反例字符串，方法可按下方步骤重跑。

## 根因分析

- 已确认：Office 单元格换行不实现 CJK 禁则；PPT 渲染时会按自身字体度量再折行，即使文本里已有换行符也可能在别的点断开。
- 排除过的假设：不是字体缺字（雅黑齐全）；不是列宽算错（加宽后切词位置变化但仍切）。
- 问题归属：环境或依赖（Office 排版行为），脚本侧必须自己接管断行。

## 最小修复

1. **度量**：`ImageFont.truetype('msyh.ttc', size_pt*4).getlength(text)/4` 得 pt 宽（4 倍采样减误差）；粗体用 msyhbd.ttc。
2. **tokenize**：ASCII 字母数字串与 `+-_./%&'-–—` 保持原子（DOU+、18–35、PUGV 不切）；en-dash 与数字粘连。
3. **禁则**：NO_LINE_START（，。、；：？！）】》」』%… 等）/ NO_LINE_END（（【《「『 等）；贪心断行 + 违规则回拉，**token 级**操作防丢字。
4. **写入**：预断行结果用显式 `\n` 写进单元格；PPT 设 `cell.text_frame.word_wrap = False` 禁二次折行；宽度留 `SAFETY=0.93`。
5. **行高**：`line_height_pt = size*1.36`；xlsx `row_dimensions[r].height = maxlines*LINE_PT + 12`（显式，不用 AutoFit）。
6. **守卫**：列宽总和 ≤ 幻灯片宽（16:9 = 13.333in），超了报警。示例几何：COLS_IN=[1.20,2.10,2.45,2.80,2.30,1.95]，BODY_PT=12.5。
7. **验收**：不变量测试 + 真实渲染 PNG 肉眼，两者都过才算完。

## 验证记录

- [x] 静态/不变量测试：test_wrap.py 五项断言 failures=0（含字符不丢）。
- [x] 渲染取证：PPT 导出 2560x1440 与 xlsx 剪贴板 1579x694，逐轮肉眼确认无标点行首、无切词、无裁字。
- [x] 反例留存：修复前 KOC/DOU+/18–35 切词与标点行首均实测出现。
- [ ] WPS 打开行为：未测。

## 可复用规则

- 交付级中文表格：**断行自己算，别交给 Office**；拉丁词/数字区间当原子 token；禁则集合显式维护。
- PPT 表格要 `word_wrap=False` + 预断行，否则渲染器会按自己的度量再切一遍。
- 度量用真实字体文件（Pillow getlength），比「CJK=2 宽度单位」估算准；换字体必须重度量。
- 排版结论只认真实渲染出图 + 不变量测试双签字（与行高记录互补：那条管「行够不够高」，本条管「行在哪断」）。

## 适用范围与不适用范围

- 适用：python-pptx/openpyxl 生成的混排中文表格，Office COM 出图交付。
- 不适用：纯英文窄表；浏览器渲染（CSS 有 `line-break`/`word-break` 可配，行为不同）。

## 剩余风险

- 0.93 安全边距与 1.36 行高系数是微软雅黑下的经验值；换字体/换字号要重测。
- 禁则集合按常见标点维护，生僻符号（如竖排标点）未覆盖。
- WPS 的换行行为未实测。

## 关联

- 相关记录：[[踩坑-openpyxl写的xlsx在Excel里行高被裁字]]（行高侧）、[[踩坑-Excel区域贴Chart导出空白PNG改用剪贴板或PPT导出]]（出图路径）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
