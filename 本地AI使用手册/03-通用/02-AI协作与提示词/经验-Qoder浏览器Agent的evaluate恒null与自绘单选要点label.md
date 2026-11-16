---
title: "Qoder 浏览器 Agent 实测：evaluate 恒 null、自绘单选要点 label、临时标签页会被回收"
date: 2026-11-15
domain: common
category: 03-通用/02-AI协作与提示词
status: verified
severity: low
stack: [Qoder, browser-use, Playwright, AtomGit]
tags: [浏览器自动化, 工具调用, 取证]
---

# 问题：用 Qoder 浏览器 Agent 改 AtomGit 仓库可见性，语义树和 evaluate 都不可靠

## 一句话结论

2026-11-15 本机 Qoder 0.5.6 + 浏览器连接器 1.7.7 实测：`tab.playwright.evaluate` 对字符串和函数都返回 null，读 DOM 改用 `domSnapshot()`；自绘单选（DevUI radio）在无障碍树里只有文本节点，点文本不保证切换，要点 `label:has(input[value=...])`；agent 创建的临时标签页在调试器断开后会被回收，需重建 agent 后新开页；页面 toast「操作成功」不能单独当成功证据。

## 触发条件与影响

- 项目或功能：用浏览器登录态在 AtomGit 新建仓库、把私有改成公开。
- 环境与版本：Qoder 0.5.6 桌面版；Chrome 扩展 qoder-browser-connector 1.7.7；Node REPL 里的 Browser Agent。
- 触发条件：按常规 Playwright 习惯写 `evaluate` 读 DOM，或对着 AX 文本节点直接 click 自绘控件。
- 影响范围：会误判“页面没响应/控件点不动”，进而在错误方向排查。

## 复现步骤与证据

1. `tab.playwright.evaluate("document.title")` 与传函数两种写法均返回 `null`；`tab.playwright.domSnapshot()` 返回完整 HTML，搜 `项目可见性` 能拿到 `input[type=radio][value=public|private]` 及其 checked 状态。
2. AX 树里该控件只有 `text 公开` / `text 私有`，对文本节点 `ax.click` 不改变选中态；改用 `locator('label:has(input[value="public"])').click()` 后，DOM 出现 `class="active"` 且 `input checked`。
3. 某次 `ax.click` 后报 `Debugger is not attached to the tab with id: ...`；随后 `browser.user.openTabs()` 里该标签页消失，只能重建 agent 再 `browser.tabs.new()`。`claimTab` 只接受 `openTabs()` 返回的对象，手工构造会报错。
4. 保存后页面出现 `操作成功`；刷新后单选仍为公开；另用无凭据 `GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote https://atomgit.com/zhoumoyukuai/cc-hud.git` 读到 `refs/heads/main` 才判定公开真正生效。

## 根因分析

- evaluate 返回 null：本机该版本行为，未查源码；按技能文档它属于“专家逃生口”，不要作为常规读页手段（更不能用它读凭据、Cookie、storage）。
- 自绘控件：可点击热区在 `label` 上，文本 `span` 只是展示层。
- 标签页回收：agent 创建的临时页在调试器断开/轮次结束时被清理，这是设计行为；用户页签 `claimTab` 才会在轮次结束时释放而不是关闭。

## 最小修复与可复用规则

- 读结构：`tab.playwright.domSnapshot()`；精确定位用 Playwright 的 role/label/属性选择器。
- 点自绘单选/开关：点 `label` 或 input 的宿主，不要点无障碍树里的文本节点。
- 对外写操作三件套：刷新回读 UI 状态 + 业务侧独立验证（如匿名 ls-remote）+ 保存实际命令输出当证据。
- 遇到 `Debugger is not attached`：重建 agent、新开标签页；不要原地重试有副作用的动作，先观察当前状态。

## 适用范围与不适用范围

- 适用：Qoder Browser Agent 对自带登录态的站点做自动化（2026-11-15 版本实测）。
- 不适用：其他版本/其他自动化框架；凭据字段的读写（技能明确禁止，须人工接管）。

## 剩余风险

版本升级后 evaluate 行为与标签页回收策略可能变化；本记录未覆盖跨域 iframe、下载与多浏览器并存场景。

## 关联

- 相关记录：[[03-通用/04-工程规范与安全/规则-AtomGit与GitHub差异与国内推送判据]]、[[规则-GitCode令牌只读活验用api-v5用户端点]]
- 相关分类：[[03-通用/02-AI协作与提示词/README|AI 协作与提示词]]
