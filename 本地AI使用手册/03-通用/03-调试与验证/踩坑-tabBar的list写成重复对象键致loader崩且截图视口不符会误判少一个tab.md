---
title: "uni-app 的 tabBar.list 必须是数组（重复键只会剩最后一个）；而验收时 headless 的 --window-size 与 CSS 视口不一致，按像素簇数 tab 会数错"
date: 2026-11-04
domain: frontend
category: 调试与验证
status: verified
severity: medium
stack: [uni-app H5, HBuilder X, Edge headless, CDP]
tags: [tabBar, JSON重复键, 视口不一致, 像素误判, getBoundingClientRect, 几何取证]
---

# 问题：tabBar 配了三个 tab，编译报 `getPageComponents` 崩；修好后截图又"少一个"

## 一句话结论

两件事叠在一起：①**配置错**——`tabBar.list` 写成三个同名的 `"list"` 对象（JSON 重复键只保留最后一个，
且类型应为数组），uni-app 的 `webpack-uni-pages-loader/lib/platforms/h5.js` 在 `getPageComponents` 处直接抛；
②**验收方法错**——headless Edge 的 `--window-size=390,844` 与页面实际 CSS 视口（496×751）不一致，
截图只有 390 px 宽，第三个 tab（x=331..496）被切在画面外，于是"看图数出 2 个 tab"是**假故障**。

## 触发条件与影响

- 环境：HBuilder X 5.33、uni-app Vue2 默认脚手架、项目 `wofule`（已导入为项目）
- 错误写法（原始）：
  ```jsonc
  "tabBar": {
      "list": { "iconPath": "...home.png",  "pagePath": "pages/home/home",  "text": "首页" },
      "list": { "iconPath": "...foodlist.png","pagePath": "pages/foodlist/foodlist","text": "同学" },
      "list": { "iconPath": "...my.png",     "pagePath": "pages/my/my",      "text": "我的" }
  }
  ```
  两个独立错误：**`list` 是对象不是数组**；**同层重复键 `list`** ⇒ 解析后只剩第三项，前两项消失
- 表现：控制台 `Module build failed … SyntaxError`/`at getPageComponents (…h5.js:55:14)`，页面起不来
- 正确写法：`"list": [ {…}, {…}, {…} ]`（每项一个对象，逗号分隔，末项不带逗号）

## 复现步骤

1. 前置：`pages.json` 已有 `pages` 数组且三个页面文件都存在
2. 操作：把 `tabBar.list` 写成三个同名 `"list"` 对象键 → 保存 → HBuilder 运行到浏览器
3. 预期：编译报配置类型错误
4. 实际：`getPageComponents` 抛栈（h5.js:55 → index-new.js:138 → index.js:55），Web 面板白屏

## 证据

| 取证 | 结果 |
|---|---|
| 修前编译 | `项目 wofule 编译失败`，栈顶 `getPageComponents (…uni-pages-loader\lib\platforms\h5.js:55:14)` |
| 修后编译 | `cli launch web --project …\wofule --compile true` → **`项目 wofule 编译成功`**（21:44:03） |
| 用户的 dev server（21:41 起的那个） | 自动热编译后 `http://localhost:8080/` 回 **200**，`Failed to compile` 命中 **0** |
| 渲染后 DOM（`--dump-dom`） | `.uni-tabbar__item` **3 个**；`首页/同学/我的` 文本各 1 次；第三个用 `my_selected.png`（当前页是 `pages/my/my`，选中态） |
| 6 个图标文件 | `curl` 逐个 **200**（2290/2346/2273/2283/3353/3506 B） |
| CDP 权威几何 | 视口 **496×751**、tabbar 条 `x=0 w=496 h=50`、3 个条目 `x=0/165/331 宽各165`、`可见` 全 true、`图标加载成功` 全 true、当前页标签色 `rgb(18,150,219)`（选中）其余 `rgb(153,153,153)` |
| 我的第一版"看图结论" | 截图 390×844，只见 2 个 tab ⇒ **错**，第三个在 390 px 之外 |

## 根因分析

- 已确认根因（配置）：`tabBar.list` 的类型与重复键。JSON 规范下同名键后者覆盖前者，
  uni-app 拿到的 `list` 是一个对象而非数组，`getPageComponents` 按数组遍历时炸。
- 已确认根因（误判）：`--window-size` 在 `--headless=new` 下不等于 CSS 视口宽度；
  页面按 496 px 布局，截图只导出 390 px，右侧内容被裁 ⇒ **像素簇/目视都数不出第三个 tab**。
- 排除过的假设：①"图标缺失导致第三个 tab 不显示"——6 个图标全 200 且 `naturalWidth=128`，否；
  ②"pagePath 不在 pages 里被丢弃"——三项都在 `pages` 中，否；③"tabBar 需要 color/selectedColor 才渲染"——
  默认值下三项都渲染出来了，否。
- 问题归属：**配置为用户手写错误**；**误判为我方取证方法错误**

## 最小修复

只把 `tabBar` 块换成数组，其余字节不动（含第 2 行那条 `//` 注释）：

```jsonc
	"tabBar": {
		"list": [
			{
				"iconPath": "/static/home.png",
				"selectedIconPath": "/static/home_selected.png",
				"pagePath": "pages/home/home",
				"text": "首页"
			},
			{ …foodlist… },
			{ …my… }
		]
	}
```

生成脚本里**字段之间要加逗号、末项不加**——我第一版漏了逗号，写盘前的 JSONC 校验把它拦下了，
原文件一个字节没动（这是"改前先校验再落盘"救的一次）。

## 验证记录

- [x] 编译：`项目 wofule 编译成功`
- [x] 热更新后的真实页面：200、无 `Failed to compile`
- [x] DOM：`.uni-tabbar__item` = 3
- [x] 几何（CDP `getBoundingClientRect`）：3 个条目 x=0/165/331 各宽 165，全部 `可见=true`，图标全部加载成功
- [x] 无常驻残留：CDP 探针的 headless Edge 已随脚本退出（近期 msedge 无、9777 端口 0）；
      用户自己的 dev server（PID 35388）**未动**

## 可复用规则

1. **uni-app 配置里凡是"多项"的字段都是数组**：`pages`、`tabBar.list`、`condition.list`、
   `subPackages[].pages`。写成重复同名键 = 只留最后一个，且类型错会让 loader 抛栈。
2. **数元素要用 DOM/几何，不要用像素**：`document.querySelectorAll(...).length` +
   `getBoundingClientRect()` 才是权威；像素簇会被整条背景连成一片（本次 `runs=[(0,389)]`）而失效。
3. **headless 截图前先核对 CSS 视口**：`window.innerWidth/innerHeight` 与图片尺寸不一致时，
   画面外的内容**等于没验**——要么把 `--window-size` 调成真实视口，要么直接按 DOM 断言。
4. **生成 JSON/YAML 的脚本，落盘前必须解析校验**（uni-app 的两个配置文件是 **JSONC**，
   校验要先剥 `//` 注释再 `json.loads`，否则会把正常文件误判为坏）。

## 适用范围与不适用范围

- 适用：uni-app / 小程序 `app.json` 一类"数组型配置"的编写与验收；任何 headless 截图取证
- 不适用：纯服务端配置
- 例外：`.uni-tabbar__item` 是 uni-app H5 的类名，小程序端要换选择器

## 剩余风险

- **启动页是 `pages/my/my`**（`pages` 数组第一项），所以应用一打开就落在"我的"tab，
  而 tabBar 顺序把"首页"排第一。两者不一致通常是笔误，但改它会改变应用行为，**已交回用户决定，未动**。
- 第二个 tab 文案是"同学"（配的是 `foodlist`），疑为占位/打趣，未改。

## 关联

- 相关记录：[[踩坑-HBuilder把容器目录当项目致报缺少pages.json且CLI传未导入路径假阴性]]（同一项目的上一课）、
  [[踩坑-按URL子串判读写致register被当读端点探测时写入用户库]]（同族：取证方法本身会造出假结论）
- 相关分类：03-通用/03-调试与验证
- 本机产物：`02_证据日志\wofule-pages.json.tabBar改前`、`03_工具脚本\{fix_wofule_tabbar.py,cdp_tabbar_probe.js}`、
  `%TEMP%\dsh_shot\{wofule_h5.png,dom.html}`
