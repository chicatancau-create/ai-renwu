---
title: "flex/grid 的 min-width:auto 沿轨道链把兄弟卡片撑宽"
date: 2026-11-15
domain: frontend
category: 01-前端/02-CSS与视觉
status: verified
severity: high
stack: [Vue 3, CSS Grid, Flexbox, Edge 157]
tags: [响应式, 横向溢出, min-width, grid轨道, 遮挡]
---

# 问题：一个固定宽度的子网格把同级的其它卡片一起撑宽，窄屏整页横向溢出；同一族问题还会在桌面档把邻列文字压住

> 两个缺陷都是**量出来的**，不是看出来的：`over=438`、`cover=33`。肉眼看桌面版只觉得「最长 6 天」有点挤，看不出被压了 26px。

## 一句话结论

`flex`/`grid` 项默认 `min-width:auto`，一个不可收缩的深层子元素会**沿轨道链一路向上放大到祖先网格的 `auto` 轨道**，把本该独立的兄弟卡片一起撑宽；反过来，轨道被 `minmax()` 上限压窄而内容不可收缩时，文字会以 `overflow:visible` 画到邻列下面——此时 `scrollWidth - clientWidth` 仍是 0，**只查溢出永远发现不了遮挡**。

## 触发条件与影响

- 项目或功能：Vue 3 习惯打卡应用的周视图矩阵（表头 + 4 行 × 7 格 + 统计列 + 操作列）与统计页明细表
- 环境与版本：Edge 156/157 headless，`Emulation.setDeviceMetricsOverride`，`deviceScaleFactor=1`
- 触发条件：矩阵格子用固定 px（`36px`×7 + `6px`×6 = 288px），行用 grid 四列，页面外层也是 grid/flex
- 影响范围：390 / 480 / 720 / 901 / 1024 / 1280 六档视口下的打卡页与统计页

## 复现步骤

1. 前置条件：`npm run build` + `vite preview`（预览服务读的是 `dist/`，**改完源码不重新 build 就量不到**）
2. 操作或命令：`node tools/headless-cdp-verify/examples/measure-overflow.mjs`
3. 预期结果：每档视口 `over <= 0`
4. 实际结果（修前）：

```
OVER   390px  #/        over= 438  div.card.week-card@813 div.week-head@792 div.week-nav@792 button.btn-plain@623
OVER   390px  #/stats   over= 152  table.stats-table@527 caption.@527 thead.@526 tr.@526
OVER   480px  #/        over= 348  div.card.week-card@813 ...
OVER   480px  #/stats   over=  62  table.stats-table@527 ...
OVER   720px  #/        over= 108  div.card.week-card@813 ... span.future-hint@792
```

注意第一行：溢出 438px 的「元凶」被报成 `.week-card`——它自己内容很窄，纯粹是被撑宽的**受害者**。

## 证据

逐元素几何 + 计算样式的实测链（390px 视口，`clientWidth=375`）：

| 元素 | 实测 | 说明 |
| --- | --- | --- |
| `.habit-board` | 盒子 `w=347`，但 `grid-template-columns` 计算值 = **783px** | 单列 `auto` 轨道被撑开 |
| `.card.week-card` | `left=30 w=783 right=813` | 兄弟受害者，`813-375=438` 正是 over |
| `.habit-list` | `w=783`（内容 min 749 + padding 32 + border 2） | 最小宽度来源 |
| `.habit-row` | 轨道 `150px 288px 200px 75px` + 3×12 gap = **749px** | `.cells` 的 288 = 7×36+6×6 |

即 `.cells`(min-width:auto→288) → `.habit-row`(749) → `.habit-list`(783) → `.habit-board` 的 `auto` 轨道(783) → 所有兄弟卡片 783 宽 → `right=813`。

**A/B 验证（关键）**：只加 `grid-template-columns:minmax(0,1fr)` + `.habit-board>*{min-width:0}` 后，兄弟卡片回缩到 281，但 `over` 只从 438 降到 **421**——矩阵自身仍占 749。证明**「切断轨道放大」和「让深层内容本身可收缩」两件事缺一不可**，只做其中一半会以为修好了。

桌面档的遮挡是另一副面孔（修前）：

```
### vw=1280   row0 grid=190px 288px 240px 100px
row0 statsBox=715..955 contentRight=993 actionsLeft=967  内部溢出=38  被操作列盖住 26px
### vw=901    grid=165.344px 288px 215.328px 90.3281px   遮挡 51~58px（更严重）
```
`.stats` 的 `overflow` 是 `visible`，所以「最长 6 天」直接画到「编辑」按钮底下，而 `over=0`。

## 根因分析

- 已确认的根因：
  1. `flex`/`grid` 项的 `min-width:auto` 使深层固定 px 内容成为不可突破的下限，并沿 `auto` 轨道向上传播。
  2. 轨道用 `auto` 时，**表头和行是两份独立 grid**，各自按自己的内容求解 → 同一份声明量出不同轨道（表头 `220/301/260/37` vs 行 `190/288/240/100`），星期条整体右移 30px。
  3. `minmax(200px,260px)` 的上限低于内容最小宽度（278px）且 `overflow:visible` → 遮挡而非溢出。
- 排除过的假设：一开始怀疑是 `.habit-list` 上写死的 `min-width`，实测该处并无此声明。
- 问题归属：本次修改引入（矩阵与统计列是新写的）

## 最小修复

1. **切断放大链**：外层 `grid-template-columns: minmax(0, 1fr)`，且 `.habit-board > *{min-width:0}`、`.card{min-width:0}`。
2. **让矩阵本身可收缩**：格子尺寸抽成 `--cell-size` / `--cell-gap` 两个变量供表头与行共用，窄档降到 `32px/5px`；≤900px 时行改为 `flex-wrap` 三行堆叠（身份+操作 / 7 格 / 统计），用 `order` 与表头逐行对齐。
3. **轨道与内容无关**：第 2 列用 `calc(var(--cell-size)*7 + var(--cell-gap)*6)`、第 4 列固定 `104px`，表头与行写**逐字相同**的声明，保证逐列相等。
4. **统计列内部两行化**：`.stats` 由 `display:flex` 改 `display:grid; grid-template-columns: max-content 1fr max-content`，`max-content` 列恒等于内容宽度，不可能越出自己的格子。
5. **表格类真需要横滚的**：外面套 `overflow-x:auto` 容器 + 表格给 `min-width`，让页面不溢出、表格在自己容器里可横滚。**不用 `overflow-x:hidden` 裁掉，也不用 `display:none` 藏列。**

## 验证记录

- [x] 构建：`npm run build` 通过
- [x] 端到端：`measure-overflow.mjs` 24 个「视口 × 路由」组合 `over=0 且 cover=0`（Edge 157，2026-11-15 复跑）
- [x] 桌面未退化：1280px 下 `.habit-row` 与 `.list-head` 轨道逐列相等（`179px 288px 247px 104px`），`.stats` 内容右边缘 951 < `.row-actions` 左边缘 963
- [x] 目视复核：Word 实转 PDF 逐页看图，确认「最长 6 天」完整可读
- [ ] 真实浏览器竖向滚动条下的临界窗口：未测（见剩余风险）

## 可复用规则

1. 窄屏出现横向溢出时，**先量「溢出元素是不是受害者」**：沿祖先链找 `grid-template-columns` 的计算值，若某个 `auto` 轨道远大于该元素内容，真凶在兄弟分支。
2. 判据必须同时量两件事：`scrollWidth - clientWidth`（溢出）**和**兄弟列水平重叠像素（遮挡）。只量前者会漏掉 `overflow:visible` 的压列。
3. 判定「遮挡」要排除换行情形：只在两个元素**垂直区间相交**时才计重叠，否则堆叠布局会给出假阳性（实测 820px 堆叠档一度报 `被盖住 100px`）。
4. 表头与行若各自是独立 grid，轨道声明要么逐字相同，要么抽成一个 CSS 变量供两处 `var()` 引用；靠「两份一样」维持对齐没有机制保障。
5. 断点位置由内容地板宽度算出来，不要照抄 720px：本例四列地板之和 760px + 卡片内边距 ≈ 需 855px 视口，所以堆叠档必须提到 **900px**，721–900 这一段本来就会溢出。

## 适用范围与不适用范围

- 适用：CSS Grid / Flexbox 组成的多列表格型布局、仪表盘、看板矩阵；`minmax()` 定轨道的内容型页面
- 不适用：单列文档流布局（不会出现轨道放大链）；`table` 元素自身（它的收缩规则不同，直接套滚动容器即可）

## 收尾复验（2026-11-15 把当时的三条风险逐条量掉）

1. **「真实浏览器竖向滚动条只剩 18px 余量」→ 实测为自我消解，不是隐患。**
   真窗口（不做 `setDeviceMetricsOverride`）实测 `innerWidth=875 / clientWidth=860 / 滚动条=15 / over=0`。
   再用模拟视口扫断点两侧：`890→堆叠档 over=0`、`901 / 906 / 916 / 920 / 1024 / 1280→四列档 over=0`。
   结论：滚动条把布局视口推下 900 断点时，**堆叠档接手**，所以 901–906 窗口不会翻成溢出。
   但这条保护依赖「断点判据是 `clientWidth`」——若有人把断点改成按 `100vw` 或 JS 里读 `innerWidth` 判断，保护就失效。
2. **「`.stats` 列宽按行浮动、进度条右边缘行间错位」→ 确认是真缺陷并已修。**
   修前实测四行右边缘两档 `[911, 918]`、错位 7px，根因是 `grid-template-columns: max-content 1fr max-content` 里第 3 列被 `80%`(24.75px) 与 `100%`(31.8px) 撑出两种宽度，中间 `1fr` 跟着变。
   改法：两侧换成定宽 `66px 1fr 40px`（上限依据：`本周 7/7` 的 done 与 target 都 ≤7 不会出现三位数；`100%` 是最长百分比）。
   改后每档视口都只有一组右边缘值（1280 下 `barRights=[903]`），并**在验收脚本里加了回归锁**：`各行进度条右边缘逐行相等` + `统计文字不被操作列压住`。
3. **「打卡格 32px 低于 WCAG 44px」→ 给出实测边界而非笼统风险。**
   390px 下实测 `cell=32x32 gap=5`。`WCAG 2.5.8（24px，AA）= PASS`；`WCAG 2.5.5（44px，AAA）= FAIL`。
   44px 在本布局**数学上不可达**：`7×44 + 6×5 = 338 > 可用 305px`。借 5px 间距最多只能扩到 37px 仍不达 44，故不改，改为记录「AA 达标、AAA 受 7 列矩阵宽度约束不可达」。

## 剩余风险

- 第 4 列固定 104px，将来往操作列加第三个按钮会在 104px 内折行而不是撑开列（属设计约束，非当前缺陷）。
- 表头与行的轨道对齐靠「两份逐字相同的声明」维持，无机制强制；更耐用的做法是抽成 `.habit-list` 上的一个 `--row-cols` 自定义属性供两处 `var()` 引用。
- 触屏无 hover，热力格当日明细在触屏上只能走明细表的点击展开；本条**未实测**（本机无触屏环境）。
- 每行是独立 grid，`.stats` 定宽后行间已对齐，但行间列宽不再随内容自适应，超长百分比（如未来改成 `100.0%`）会顶到 40px 上限。

## 关联

- 相关记录：`01-前端/09-测试与质量/踩坑-自写CDP探针的七种假阳性-真浏览器取证.md`（同一会话；报红的三条里两条是探针错，溢出与遮挡两条才是真缺陷）
- 相关分类：`01-前端/09-测试与质量`
- 相关代码、命令或文档：`E:\fullstack-code\tools\headless-cdp-verify\examples\measure-overflow.mjs`、`measure-overlap.mjs`；被测代码 `E:\fullstack-code\Web\vue\src\components\habit\{HabitRow,HabitList}.vue`、`src\views\habit\HabitStats.vue`
