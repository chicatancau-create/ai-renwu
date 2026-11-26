---
title: "OpenRevo 插件页开发：相对路径不通 / 面板惨白 / config BOM 三条硬规矩"
date: 2026-11-20
domain: common
category: 调试与验证
status: verified
severity: medium
stack: ["OpenRevo 0.9.8", "Tauri", "WebView2", "PowerShell", "Python"]
tags: ["OpenRevo", "插件", "WebView2", "BOM", "相对路径", "iframe", "srcdoc"]
---

# 问题：OpenRevo 插件页开发的三条硬规矩（相对路径不通 / 惨白 / config 写坏）

## 一句话结论

OpenRevo 插件页里的**相对路径不指向插件目录**（会落到宿主根路由，返回宿主主界面）；插件 tab 是**独立 WebView2 页面不继承宿主皮肤**，写 `background: transparent` 就惨白；改宿主 `config.json` **绝不能用带 BOM 的写法**，否则宿主停止保存配置。三者都已在本机复现、定位、修复并验证。

## 触发条件与影响

- 项目或功能：OpenRevo 整机控制中心（`D:\open-revo\open-revo.exe`）的插件页开发与配置维护
- 环境与版本：OpenRevo v0.9.8，Windows 11，WebView2 157.x，当前 shell 为 Medium 完整性（非管理员）
- 触发条件：①插件页用相对路径引同插件目录的 html/json；②插件页面 `html,body` 用 `background: transparent`；③用 `Set-Content -Encoding UTF8` 写 `%APPDATA%\OpenRevo\config.json`
- 影响范围：①iframe 显示成宿主主界面、`fetch` 拿不到插件文件；②面板白底浅字看不清；③宿主全部配置无法保存（`已阻止覆盖原文件`）

## 复现步骤

1. 前置条件：插件目录 `%APPDATA%\OpenRevo\plugins\<id>\` 下放 `index.html`（tab 入口）和另一个 `colors.html`
2. 操作：在 `index.html` 写 `<iframe src="colors.html">`，切到该插件页签
3. 预期结果：iframe 显示 `colors.html` 的内容
4. 实际结果：iframe 里是宿主主界面（状态总览/显卡模式/电源管理那一整套）

## 证据

- `fetch('tasks.json')` 报 `Unexpected token '<', "<!doctype "... is not valid JSON` —— 返回的其实是宿主 `index.html`
- 宿主日志刷：`[ERROR] [CONFIG] Cannot load configuration; original file preserved: expected value at line 1 column 1`
- 损坏后的 config 文件前 8 字节为 `EF BB BF 7B 0D 0A 20 20`（BOM + `{\r\n  `）
- 修好 BOM 后又出现：`[ERROR] [CONFIG] Configuration save failed: 配置读取失败，已阻止覆盖原文件：expected value at line 1 column 1`
- 惨白页特征：`html,body{background:transparent}`；正常页都给了实色深底（`#06090e` / `#0b0f17` / `#1c232e` / `#0f172a` / `#23303f`）

## 根因分析

- **已确认的根因 1**：宿主把未知相对路径当自己的路由兜底返回主页面；`revo://localhost/<插件id>/<文件>` 自定义协议也没走通。插件页读自有文件的唯一可靠通道是 IPC `read_plugin_file{pluginId,path}`，而它读的是 `%APPDATA%\OpenRevo\plugin_storage\<id>\<path>`，不是插件目录。
- **已确认的根因 2**：宿主皮肤 CSS 只注入主文档 `<style id="openrevo-theme-skin">`，**不注入**插件 tab 的独立 WebView2 页面；WebView2 默认白底 → `background: transparent` 直接露白，浅色文字等于惨白。
- **已确认的根因 3**：Windows PowerShell 5.1 的 `Set-Content -Encoding UTF8` 会写 BOM；宿主 Rust 侧 serde 解析 BOM 开头的 JSON 失败，于是 `original file preserved` 并阻止后续所有保存。

## 修复

1. **相对路径**：构建期把子页面转 base64 内嵌进入口 `index.html` 的 `<script id="colorsB64" type="text/plain">` 容器，运行时解码后赋给 iframe 的 `srcdoc`。base64 顺便规避 `</script>`、反引号、`${}` 的转义问题。实测 95KB 子页 → 入口页约 140KB，可接受。可复跑脚本：`G:\AIrenwu\OpenRevo插件整理\工具\build_colors.py`。
2. **惨白**：插件页 `html,body` 一律给实色深底（如 `#0b1017`）。批量修法脚本：`G:\AIrenwu\OpenRevo插件整理\工具\fix_plugin_darkbg.py`——正则把 html/body 规则块里的 `background: transparent` 换成实色，无匹配则追加兜底 `<style>`，用 `/*darkbg-patch*/` 标记防重复。
3. **config BOM**：一律用 Python `io.open(p,'w',encoding='utf-8',newline='\n')` 读写；读也不能用 PowerShell `Get-Content -Raw | ConvertFrom-Json`（把无 BOM UTF-8 当 GBK，中文乱码 + JSON 语法错）。
4. 附带：宿主运行时会持有内存态并回写 config，**运行中直接改的键可能被覆盖**，能用 IPC 改就别动文件。

## 验证结果

- `build_colors.py` 跑完后，在真实宿主里「外观中心 → 配色工坊」页签在**主面板**与**独立视窗**两种形态下都正常渲染（截图 `shot-main-colors.png`、`shot-popout3.png`），全中文，不再出现宿主主界面嵌套。
- `fix_plugin_darkbg.py` 跑完后 `sdt-pbo-plugin-v1.1.0`、`skin-manager` 两页由白底变 `#0b1017` 深底，其余 6 页判定 `ok-existing` 未改动。
- config 修好后宿主不再报 `[CONFIG]` 错误，100 个键全部保留（仅目标键值变化）。

## 适用范围与剩余风险

- 适用：OpenRevo 0.9.8 及相近版本；同类「Tauri + 多 WebView2 子页面」的插件宿主大概率同理，但需另行验证。
- 剩余风险：插件/宿主更新会覆盖插件目录里的 `index.html`，上述 1、2 两项修复需重跑脚本；`plugin_storage` 下的数据不受影响。
- 另外两个同工程坑（已验证）：插件 manifest 里 `slot` 不能写成嵌套对象（会让整个 manifest 解析失败、插件退化成 `plugin_type: directory`、页签消失），正确写法是顶层 `target_slot` + `slot_height`、`entry` 指向 slot 页、tab 页放 `tab.entry`；Medium 完整性下 `Stop-Process`/`taskkill` 被拒，但 `(Get-Process -Id X).Kill()` 可用。
