---
title: "DSH 插件体检与修复：内核升级对齐、pnpm 迁移三层坑、inspector 抓包冲突"
date: 2026-11-15
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [DeepSeek Harness, cordis, pnpm, Windows]
tags: [插件体检, 组件红标, 热重载, 取证顺序, 元数据为2026-11-15补登]
---

# 经验-DSH插件体检修复-内核升级对齐pnpm迁移与inspector抓包冲突

> 元数据为 2026-11-15 库体检时补登（原记录无 frontmatter）。
> `status: verified` 的依据是**记录自带证据**：每个根因都落到 `file:line`
> （`lib/index.js:238` 抛 accessor 错、`:1890` 的 `captureFetch` 门控、
> `:1192` 的 `writePluginEnabled` 只改 `disabled` 一键、schema `2583`），
> 并在第 6 节给出「无新 crash log + list 无 incompat + guard 对齐 + 实际冒烟」四条收尾判据。
> 补登者未独立复现整套体检；若哪天 DSH 版本变动，按第 0 节的取证顺序重跑再引用。

> 2026-11-15 沉淀。适用：DeepSeek Harness（DSH）桌面版插件「装上了却不生效 / 启动被拒载 / 组件红标」的全量体检与修复。
> 本机事实：内核 0.2.2-rc.3；`.dsh` 已整体迁到 `D:\DevCache\.dsh`，`C:\Users\Admin\.dsh` 是 junction；GUI profile=desktop。
> 装插件入口与判包可装性见姊妹篇《经验-DSH装插件与删provider的四个动作点》；asar 取文件见《规则-Electron的app.asar可直接按头解析取文件无需asarCLI》——本篇不重复。

## 0. 体检的固定取证顺序（别凭印象下结论）
1. `dsh plugin --profile desktop list`：看实装版本与有没有 incompat 警告。
2. 启动 crash log：`C:\Users\Admin\AppData\Roaming\@deepseek-ai\dsh-desktop\logs\crash-*-host.log`，grep `incompatible` / `did not activate` / `skipping profile bundle`。**这是「插件为什么没生效」的第一证据**，比界面红标准。
3. `D:\DevCache\.dsh\guard\sync.log`：内核版本与 overrides 是否对齐。
4. 逐插件读 `cordis.patch.yml` 覆盖 + 各自 settings/config，再下结论。

## 1. 内核升级后，钉旧内核的子代理插件被整行拒载
- 症状：升级 rc.2→rc.3 后 `subagent`/`spawn` 工具消失。crash log：
  `skipping profile bundle "@deepseek-ai/dsh-subagent-codex": Plugin ...@0.2.2-rc.2 is incompatible with dsh 0.2.2-rc.3`，
  并连带 `disabling profile plugin row "tool-subagent"/"tool-subagent-fork"/...`。
- 根因：`@deepseek-ai/dsh-subagent-codex`、`dsh-subagent-claude-code`、`dsh-tool-subagent` 的 peer 区间钉死旧内核。
- 修复：**升级到同内核版本**（registry 实测有 rc.3），不要用 `dsh plugin allow-version` 豁免（那是带病运行）。
  `dsh plugin --profile desktop add @deepseek-ai/dsh-subagent-codex@0.2.2-rc.3`（包名不加引号）。
- 注意：npm `dist-tags.latest` 可能是 `0.0.1-rc.1` 占位，**别用 latest，显式写 rc.3**。
- 验证：list 无 incompat + 实际 spawn 一个子代理冒烟。

## 2. `.dsh` 迁成 junction 后，pnpm 的三层坑（装任何包都会踩）
迁移后 `node_modules` 里记录的还是旧 C 盘路径，直接 `dsh plugin add` 会连环报错：
1. `ERR_PNPM_UNEXPECTED_STORE`：`DSH_HOME` 指到 D 盘会让 pnpm 自动选 `D:\.pnpm-store`，与 `.modules.yaml` 记录的 C store 冲突。
   **`npm_config_store_dir` 环境变量在 pnpm v11 被忽略**，要写进 `profiles\desktop\pnpm-workspace.yaml`：
   `storeDir: C:\Users\Admin\AppData\Local\pnpm\store\v11` + `packageImportMethod: copy`（跨卷禁硬链）。
2. `ERR_PNPM_UNEXPECTED_VIRTUAL_STORE`：`node_modules\.modules.yaml`（实为 JSON）的 `virtualStoreDir` 还是迁移前路径。
   改成 `D:\DevCache\.dsh\profiles\desktop\node_modules\.pnpm`。**不要整删 node_modules**（会删掉运行中 GUI 的插件文件，且非交互下 pnpm 报 `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`）。
3. 悬空 link：工作区整理把 `@local/dsh-preset-switcher` 的源码目录挪走后，pnpm 按 lockfile 旧路径重链→`cannot resolve profile bundle`。
   **要同时改三处**：`package.json` 的 link、`pnpm-lock.yaml`、`node_modules\.pnpm\lock.yaml`（`dsh plugin list` 读最后这份），再重建链接。
- 另：junction 根目录 `dir`/`Get-ChildItem` 可能报 Access denied，但 Python `os.listdir` 与子路径正常；CLI 偶发 EPERM stat 是瞬态，重试即可，不必改 env。

## 3. `cordis.patch.yml` 覆盖的两个硬语义
- **整段替换，不是深合并**：`- id: X / name: Y / config: {...}` 这种覆盖，`applyPatches` 里是 `target[key]=value`（app-boot `lib/index.js:550`），
  会把目标条目的**整个 config 对象换掉**。所以覆盖里要写全所需键；目标原本只有 `captureFetch:true` 时，覆盖写 `captureFetch:false` 正好。
- **会被别的进程重写丢掉**：11-14 另一会话重写 cordis.patch.yml（换 provider/加 presets），把 11-13 加的 `memsearch summarizeEnabled:false` 覆盖冲掉了→memsearch 回归狂刷 401。
  **体检时要复核既有覆盖还在不在**，不在就补回。memsearch 的 summarize 开关在插件 init 静态读取，改覆盖后需重启/重激活才生效。

## 4. inspector × billion-context 的 fetch 冲突（组件红标但没装坏）
- 症状：插件页「NodeJS 诊断」异常，`Error: inspector: globalThis.fetch is an accessor and cannot be observed safely`；同 bundle 的会话数据诊断/统计视图正常。
- 根因：billion-context 给 `globalThis.fetch` 装了 accessor（re-arm 保护，`dist/agent/dsh-native.js`，env `BILI_RECLAIM_FETCH_PATCH` 默认开）；
  experimental-inspector 的 `installFetchObserver` 硬拒 accessor（`lib/index.js:238` 抛错）→整个组件启用失败。两个都没坏，是不兼容。
- 修复：desktop `cordis.patch.yml` 加覆盖 `- id: experimental-inspector / name: '@deepseek-ai/dsh-experimental-inspector' / config: captureFetch: false`。
  门控在 `lib/index.js:1890`（`captureFetch ? installFetchObserver(...) : void 0`），schema `2583` 支持。关掉后 Console/会话数据/Cordis 树照常，只损失 DevTools 抓 fetch。
- 备选（不推荐）：`BILI_RECLAIM_FETCH_PATCH=0` 保抓包但关掉 bili 的 re-arm 保护；改 bili/重打 asar 太侵入。

## 5. 配置热重载不会重试「已失败」的组件——要手动拨开关
- 现象：改好 cordis.patch.yml 后，开机就已启用失败的组件**仍红着**。
- 根因：`dsh-hmr` 默认监听 cordis.patch.yml 热 recompose，但**不会自动重试一个已经 failed 的条目**。
- 修复：把该组件开关**关掉再打开**。`writePluginEnabled`（plugin-manager `lib/index.js:1192`）只改 `disabled` 这一个键、保留 config 覆盖；
  随后 `reload→hmr.reconcileProfile` 会**重新从磁盘读** patch 并 recompose→带新配置激活。实在不行重启 GUI 必然生效。
- 判据：改完别只看界面红标就判「没修好」；先确认配置真被合成（读 applyPatches 语义），再给组件一次重激活。

## 6. 收尾判据
- 「无新 crash log + list 无 incompat + guard 对齐 + 实际冒烟」四条都过，才算修好；界面绿标不是充分证据。
- 潜伏项单独列、不硬修：失效的 deepseek 官方 key（无活跃依赖时不动）、bili 对某模型缺输出上限真实值（不猜）。
