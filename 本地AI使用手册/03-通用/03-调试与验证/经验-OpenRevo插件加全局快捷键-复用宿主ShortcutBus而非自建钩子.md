---
title: "OpenRevo 插件要加全局快捷键：复用宿主 Shortcut Bus，别自建键盘钩子"
date: 2026-11-14
domain: common
category: "调试与验证 / 桌面端插件"
status: verified
severity: medium
stack: ["OpenRevo", "Tauri v2", "Rust", "Windows", "WebView2"]
tags: ["OpenRevo", "快捷键", "全局热键", "Tauri IPC", "插件", "WH_KEYBOARD_LL"]
---

# 问题：给 OpenRevo 的功能（如「一键强冷」）加快捷键，插件该怎么做

## 一句话结论

宿主已内置 Universal Shortcut Bus（`WH_KEYBOARD_LL` 全局钩子），插件只需调
`register_custom_shortcut({ binding })` 注册一条 `ShortcutBinding`，动作直接用宿主原生
`ShortcutAction` 枚举即可；自建 `keydown` 监听或 `PluginEvent` 转发都做不到「面板关闭后仍生效」。

## 触发条件与影响

- 项目：OpenRevo v0.9.7（`D:\open-revo\open-revo.exe`，Tauri v2 单文件）
- 插件目录：`%APPDATA%\OpenRevo\plugins\<id>\`（`manifest.json` + `index.html`）
- 触发条件：想让面板里的功能支持用户自定义全局快捷键
- 影响范围：仅插件侧，不改宿主

## 复现步骤

1. 前置：OpenRevo 常驻运行（托盘），插件 iframe 通过 `window.parent.__TAURI_INTERNALS__.invoke` 调宿主。
2. 操作：插件内执行
   `invoke("register_custom_shortcut", { binding: { id, name, combo: "Ctrl+Alt+F", action: { type: "ToggleFanBoost" }, osd: true, enabled: true, swallow: false, plugin_id: "my-plugin" } })`
3. 预期：返回 `true`，按下 Ctrl+Alt+F 触发一键强冷。
4. 实际：符合预期（契约层已用 mock 全量验证；实机触发见「剩余风险」）。

## 证据

- 权威源码（Gitee `faintonce/open-revo` master，GPLv3）：
  - `src-tauri/src/commands/shortcut_cmd.rs`：4 条命令签名与报错文案
  - `src-tauri/src/system/shortcuts/types.rs`：`ShortcutBinding` 8 字段、`ShortcutAction` 邻接标签枚举、`map_key_to_vk` 键名表
  - `src-tauri/src/system/shortcuts/manager.rs` / `dispatcher.rs`：同 id 覆盖、`swallow` 语义、`plugin_id` 生命周期
- 二进制佐证（`open-revo.exe` 字符串表）：插件桥命令白名单含 `register_custom_shortcut(binding)` /
  `unregister_custom_shortcut` / `trigger_shortcut_action` / `check_hotkey_conflict`；
  `struct ShortcutBinding with 8 elements`；`Initialized OpenRevo Universal Shortcut Bus (loaded {} persistent custom shortcuts)`。
- 本地存档：`G:\AIrenwu\01_任务归档\2026-11-14_OpenRevo快捷键插件\02_证据日志\`

## 根因分析

- 已确认：宿主快捷键子系统与插件桥是两套独立设施。快捷键执行发生在宿主常驻进程的低级键盘钩子里，
  **与插件页面是否存活无关**；而 `PluginEvent` 只是把事件 `emit` 给插件，插件 iframe 不在就无人处理。
- 排除：`manifest.json` 里声明 `shortcuts` 数组（宿主有该字段，但安装版解析严格度无法离线验证，
  写错会导致整个插件加载失败，风险高于收益）。
- 问题归属：新知识，非缺陷。

## 最小修复

插件只做「配置界面 + 幂等注册」：

1. 固定 id 前缀（`hb:<动作>`）+ `plugin_id`，利用「同 id 覆盖」实现改键；
2. 每次打开面板做一次对账：`get_registered_shortcuts()` → 清掉本插件残留 → 重放本地期望绑定（宿主重启丢注册可自愈）；
3. 键位录制严格对齐宿主 `map_key_to_vk`：只允许 A-Z / 0-9 / F1-F24 / 固定特殊键表，
   **数字小键盘没有映射，必须直接拒收**，否则注册必然失败；
4. 组合键匹配是**严格修饰键全等**，`Ctrl+F` ≠ `Ctrl+Shift+F`，冲突预检按整串比对。

## 验证记录

- [x] 静态检查：`node --check` 抽取脚本；`el("id")` 与 HTML id 全量比对（0 缺失/0 冗余）
- [x] 单元/契约测试：`node 03_工具脚本/run_tests.js` → 20 passed / 0 failed（mock 严格复刻 Rust 命令返回与报错）
- [x] 部署：`install.ps1` 落位 3 文件，manifest 可解析，源与目标 md5 一致
- [ ] 实机触发：需重启 OpenRevo 后手动按一次键（未执行）

## 可复用规则

1. 给桌面端插件加全局热键，**先查宿主是否已有全局钩子/快捷键总线**（搜 `hotkey|shortcut|accelerator|RegisterHotKey`），
   有就复用；插件内的 `keydown` 只在聚焦时有效，不能当全局快捷键用。
2. 逆向宿主 API 时，**优先找开源仓库拿权威结构体定义**，二进制字符串只作交叉验证；
   Rust serde 的字段名在 release 构建里常被合并/优化掉，靠扫指针表猜字段性价比极低。
3. Tauri v2 **只把命令参数名做 camelCase→snake_case 转换，不转换嵌套结构体字段**：
   `plugin_id` 写成 `pluginId` 会被静默忽略（`Option` 变 `None`），不报错但行为不对。
4. PowerShell 5.1 读取**无 BOM 的 UTF-8 .ps1**（含中文）会按 GBK 解码，报「缺少右 `}`」这类假语法错误；
   给脚本加 UTF-8 BOM 即可。

## 适用范围与不适用范围

- 适用：OpenRevo 0.9.x 插件开发；同类 Tauri v2 桌面应用「插件复用宿主能力」的架构判断。
- 不适用：宿主未提供快捷键总线时（只能自建 `RegisterHotKey`，需处理冲突与管理员权限）；
  需要「按下快捷键后执行插件私有逻辑」且插件必须常驻的场景（当前宿主无持久后台 iframe）。

## 剩余风险

- 安装版 v0.9.7 与仓库 master 可能存在细微差异；插件已做错误透传，失败时面板直接显示宿主原文。
- 持久化依赖宿主把 `custom_shortcuts` 写入 `config.json`（boot.log 有佐证，未逐条验证）；
  开机到首次打开面板之间可能短暂失效，打开面板即自动补回。
- 实机触发未验证。

## 关联

- 相关记录：`2026-11-11_OpenRevo电池限充`、`2026-11-13_OpenRevo插件优化`
- 相关代码：`G:\AIrenwu\01_任务归档\2026-11-14_OpenRevo快捷键插件\04_产物\hotkey-binder\`
- 相关文档：同目录 `02_证据日志\宿主接口契约.md`
