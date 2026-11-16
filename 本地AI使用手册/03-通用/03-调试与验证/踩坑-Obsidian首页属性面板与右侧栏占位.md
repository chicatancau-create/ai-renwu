---
title: "Obsidian 首页属性面板与右侧栏占位"
date: 2026-11-04
domain: common
category: "调试与验证"
status: verified
severity: low
stack:
  - Obsidian
  - CSS
  - Homepage
tags:
  - Obsidian
  - CSS
  - 启动页
---

# 问题：Obsidian 首页已套用 CSS，YAML 属性面板仍占据首屏

## 一句话结论

`cssclasses` 只挂在 Markdown 预览根节点上，属性面板在它的外层；要隐藏属性必须用 `:has()` 从 `.workspace-leaf-content` 向上匹配。首页右侧栏占位则用 `.workspace:has(.life-guide-home) .workspace-split.mod-right-split` 在首页单独隐藏。

## 触发条件与影响

- 项目或功能：Obsidian 知识库启动首页、章节阅读页
- 环境与版本：Obsidian 1.15.0，Homepage 3.6.0，Windows
- 触发条件：笔记带 YAML frontmatter，且通过 `cssclasses` 设置专属样式
- 影响范围：属性面板占据首屏、重复显示标题、右侧栏压缩正文宽度；不影响正文数据

## 复现步骤

1. 前置条件：Vault 中新建首页笔记，frontmatter 写 `cssclasses: [life-guide-home]`
2. 操作或命令：设置 Homepage 启动页，重启 Obsidian
3. 预期结果：启动后直接显示首页，只显示正文和卡片
4. 实际结果：首页 CSS 已生效，但顶部仍显示“笔记属性”，右侧栏也占用宽度

## 证据

- 启动窗口标题：`00-首页 - OBsidian - Obsidian 1.15.0`
- 首页截图：`.work/screenshots/obsidian-home-live.png`
- 章节截图：`.work/screenshots/obsidian-chapter.png`
- 仅写 `.life-guide-home .metadata-container { display:none; }` 时，属性面板仍然可见

## 根因分析

- 已确认的根因：`cssclasses` 加在 `.markdown-preview-view` 上，属性容器 `.metadata-container` 位于其外层，因此 `.life-guide-home .metadata-container` 匹配不到
- 排除过的假设：不是 CSS 片段未启用；卡片样式已生效，说明片段本身加载正常
- 问题归属：Obsidian DOM 结构导致的样式作用域问题

## 最小修复

给所有指南笔记增加 `cssclasses: [life-guide-note]`，并用 `:has()` 从外层容器匹配：

```css
.workspace-leaf-content:has(.life-guide-note) .metadata-container {
  display: none;
}

.workspace:has(.life-guide-home) .workspace-split.mod-right-split {
  display: none;
}
```

同时隐藏重复的内联标题：

```css
.life-guide-note .inline-title {
  display: none;
}
```

Homepage 3.6.0 的 `data.json` 使用 `version: 3`，启动文件路径不带 `.md`：

```json
{
  "value": "高性价比人生指南/00-首页",
  "kind": "File",
  "openOnStartup": true,
  "view": "Reading view"
}
```

## 验证记录

- [x] 格式化或静态检查：首轮 293 个、最终 295 个 Markdown 文件的链接与标题锚点检查，0 断链
- [x] 类型检查或编译：不适用
- [x] 单元、集成或端到端测试：34 章、767 条、9 篇专题数量核对通过
- [x] 构建：不适用
- [x] 启动或手动回归：实际启动 Obsidian，自动进入 `00-首页`；首屏显示四种收益、九大主题、六个高频入口；章节页属性面板和重复标题已消失

## 可复用规则

1. Obsidian 的 `cssclasses` 只作用于预览根节点；需要隐藏属性、状态栏或侧栏时，用 `.workspace-leaf-content:has(.你的类名)` 或 `.workspace:has(.你的类名)` 向上匹配。
2. 首页样式和正文样式分开两个 class：`life-guide-home` 控制首页，`life-guide-note` 控制普通笔记；不要用全局 `.metadata-container`，否则会影响同 Vault 其他笔记。
3. 安装 Homepage 前先核对 `manifest.json` 的 `minAppVersion`；Obsidian 启动器可能自动升级，实际运行版本要看日志里的 `obsidian-x.y.z.asar`，不能只看安装目录 exe 的版本。
4. Homepage 3.x 的启动路径不带扩展名；4.x 改为带扩展名，配置不能混用。
5. 验证“启动页是否生效”要看窗口标题是否变成目标笔记名，不能只看进程是否启动。

## 适用范围与不适用范围

- 适用：Obsidian 1.15 附近的桌面版、使用 Homepage 3.x、通过 `cssclasses` 做单页样式
- 不适用：Obsidian 移动端未验证；Homepage 4.x 的配置字段不同；使用主题自带布局插件时可能冲突

## 剩余风险

- 浅色主题已完成首页与章节页截图验证；样式使用 Obsidian 变量，深色与浅色均可读
- Homepage 3.6.0 低于最新 4.6.0，但当前 Obsidian 1.15.0 实测可用；升级插件前需重新核对 `data.json` 版本和路径格式
- 强制结束 Obsidian 进程时不会写窗口状态，日志可能出现 `ENOENT ...<vault-id>.json`；正常退出后由应用自行生成

## 项目归档（2026-11-15）

- 成品：`E:\OBsidian\高性价比人生指南`
- 规模：34 章、767 条、9 篇专题、239 份核实记录；可见 Markdown 295 个
- 证据统计：A 495、B 220、C 52
- 性能：冷启动、热启动到首页均约 1.43 秒；仅 1 个社区插件
- 外观：深色、浅色、1366×768 等效视口均完成截图检查
- 验收材料：`04-来源与维护/验收报告.md` 与 `04-来源与维护/验收截图/`
- 保留工具：`.work/build_guide.py`、`.work/build_nav.py`、`.work/validate_content.py`、`.work/full_audit.py`、`.work/measure_startup.py`
- 已清理：一次性截图、临时主题配置、启动/截图脚本、审计输出和外部链接临时报告

## 关联

- 相关记录：[[踩坑-执行环境Start-Process子进程在工具会话结束时被连带回收]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：`E:\OBsidian\.obsidian\snippets\gaoxingjia-home.css`、`.work/build_guide.py`、`.work/build_nav.py`、`.work/validate_content.py`
