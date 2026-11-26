---
title: "DSH 插件 package.json 带 UTF-8 BOM，整个 bundle 被内核静默跳过（工具与界面按钮一起消失）"
date: 2026-11-20
domain: common
category: 调试与验证
status: verified
severity: high
stack: [DeepSeek Harness, Node.js, PowerShell, JSON, YAML]
tags: [BOM, package.json, profile bundle, cordis.patch.yml, skippedBundles, PowerShell写文件, 插件消失]
---

# 问题：DSH 插件 package.json 带 UTF-8 BOM，整个 bundle 被内核静默跳过（工具与界面按钮一起消失）

## 一句话结论

用 PowerShell（5.1 的 `Set-Content -Encoding UTF8`）改过插件 `package.json` 后，文件头多了 `EF BB BF`；DSH 内核 `loadProfileDirectory` 用 `JSON.parse` 读 bundle 清单时直接抛 `SyntaxError: Unexpected token '﻿'`，把该 bundle 记进 `skippedBundles` 并**只写 stderr、不弹窗不报红**，于是插件宿主端工具与客户端按钮一起从运行时消失——看起来像"代码有 bug / 没生效 / 需要重启"，实际是整包没被加载。

## 触发条件与影响

- 项目或功能：DeepSeek Harness（0.2.2-rc.5）profile 自定义插件 `@local/archived-cleanup`（link 依赖 + `dsh.profile.bundles` 里的 bundle patch）。
- 环境与版本：Windows；Electron 打包的 `D:\DeepSeek Harness\resources\app.asar`；profile `D:\DevCache\.dsh\profiles\desktop`；Git Bash / PowerShell 混用。
- 触发条件：用 PowerShell 写入插件的 `package.json`（例：`Set-Content -Encoding UTF8` 把版本号从 1.0.0 改成 1.0.1），文件首字节变成 `EF BB BF 7B`。
- 影响范围：该 bundle 的 `dsh.bundle.patch`（`cordis.patch.yml`）整层不参与组合 ⇒ 插件注册的 agent 工具、client slot 注册项、启动时定时任务全部消失；`global.archivedSessionIds` 之类的状态数据留在 `storages/*.json` 里没人清理，形成"幽灵行"。用户侧表现：界面按钮没了、工具调不到、重启也不恢复。

## 复现步骤

1. 前置条件：profile 的 `package.json` 的 `dsh.profile.bundles` 含 `@local/archived-cleanup`，`node_modules/@local/archived-cleanup` 是指向插件目录的 junction。
2. 操作或命令：`Set-Content -LiteralPath <插件>\package.json -Value ... -Encoding UTF8`（或用任何会加 BOM 的编辑器保存）。
3. 预期结果：重启后插件照常加载。
4. 实际结果：插件整体消失；`cordis_inspect_query client/Slots listSubTree` 里自己的 occupancy 不再出现，`host/Tool listTools` 里自己的工具不再出现，而 profile patch、依赖、junction、插件源码 `node --check` 全部正常。

## 证据

- 字节级：`[System.IO.File]::ReadAllBytes(<插件>\package.json)[0..2]` → `EF BB BF`；同目录 `index.js` 是 `69 6D 70`（`imp`），`client.js` 是 `77 69 6E`（`win`），`cordis.patch.yml` 是 `2D 20 69`（`- i`）——只有 `package.json` 有 BOM。
- 内核诊断（决定性）：用 `ELECTRON_RUN_AS_NODE=1 "D:\DeepSeek Harness\DeepSeek Harness.exe"` 动态 import `app.asar/dsh/node_modules/@deepseek-ai/dsh-app-boot/lib/index.js`，调用 `loadProfileDirectory('diag', <profile 目录>, <dsh package.json 绝对路径>, { userLayer: false })`：
  - 修前 `skippedBundles` 3 条，其中 `@local/archived-cleanup | SyntaxError: Unexpected token '﻿', "﻿{\n    \"n"... is not valid JSON`；
  - 修后 `skippedBundles` 2 条（只剩两个本来 `requirements` 版本不匹配的 `@deepseek-ai/dsh-subagent-*`），`composeEntries` 条目数 237 → 238，`archived 条目: [{"id":"archived-cleanup","name":"@local/archived-cleanup","config":{}}]`，`重复 id: []`。
- 运行时：BOM 去掉后**无需重启**，客户端 slot `sidebar.footer.action` 立刻重新出现 `archived-cleanup.clear-all`（order 100, active）；启动 5 秒扫尾也立即执行，`storages/workspace.json` 的 `mtime` 刷新、`archivedSessionIds` 变空（两个幽灵会话 id 被清掉）。
- 关键旁证：`package.json` 里的 `dsh.bundle.patch`、`exports`、`dsh.client` 声明都正确，`node --check index.js client.js` 全 exit 0 —— 所以「代码没问题但整包不生效」只能往 bundle 能否被解析这层查。

## 根因分析

- 已确认的根因：`dsh-app-boot` 的 `loadProfileDirectory` 对每个 bundle 调 `readPackageManifest`（内部 `JSON.parse`）。`JSON.parse` 不接受 BOM，抛 `SyntaxError`；按设计「Unreadable bundles ... are skipped and listed in `skippedBundles`」，于是只 `process.stderr.write(...)` 一行诊断（GUI 启动时没人看 stderr），bundle 的 patch 层被整层丢弃。
- 为什么之前没发现：①bundle patch 与 profile 的 `cordis.patch.yml` 是两套层，`cordis.patch.yml` 里查 `archived` 命中 0 是正常的（该条目本来就来自 bundle patch）；②`plugin_manager list_plugins` 只列**已组合进树**的条目，被跳过的 bundle 根本不出现，看起来像"从来没配置过"；③`dsh --profile desktop --dump-config` 对 desktop 直接报 `profile "desktop" is managed exclusively by the Electron application`，不给 dump。
- 次因（易误判）：`plugin package.json` 的 `private:true` + link 依赖 + junction 都正常，`skippedBundles` 的 reason 被截断成 `"﻿{\n    \"n"... is not valid JSON`，若只看尾部会以为是"JSON 结构错"，其实错在首字节。

## 最小修复

1. 用**不带 BOM** 的方式重写文件：

```powershell
$p = '<插件>\package.json'
Copy-Item -LiteralPath $p -Destination "$p.bom-bak-$(Get-Date -Format yyyyMMdd)"
$raw   = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8)
$clean = $raw.TrimStart([char]0xFEFF)
[System.IO.File]::WriteAllText($p, $clean, (New-Object System.Text.UTF8Encoding($false)))
```

2. 复检首字节并解析：

```powershell
$b = [System.IO.File]::ReadAllBytes($p); ($b[0..2] | % { $_.ToString('X2') }) -join ' '   # 期望 7B 0D 0A
(Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json).version
```

3. 用内核自己的加载器确认 bundle 回来了（不要把"重启看看"当验证）：

```powershell
$env:ELECTRON_RUN_AS_NODE='1'; $env:DSH_HOME='D:\DevCache\.dsh'
& 'D:\DeepSeek Harness\DeepSeek Harness.exe' '<诊断脚本>.js'   # 见上面"证据"里的 loadProfileDirectory + composeEntries 用法
```

4. 同批检查其它被 PowerShell 写过的插件文件：`package.json` 最要紧（JSON），`*.yml` 有 BOM 时 js-yaml 不影响，但 `*.json` 一律有害。

## 验证记录

- BOM 前：`skippedBundles` 含 `@local/archived-cleanup | SyntaxError: Unexpected token '﻿'`，组合条目 237，`archived 条目: []`。
- BOM 后：`skippedBundles` 2（与本次无关的两个 subagent 版本不匹配项），组合条目 238，`archived 条目` 命中，`重复 id: []`。
- 运行时无重启生效：`sidebar.footer.action` occupants 重新包含 `archived-cleanup.clear-all`；`workspace.json` 15:41:54 被改写、`archivedSessionIds` 为空（扫尾清掉了两个幽灵 id）。
- 备份：`<插件>\package.json.bom-bak-20261120`。

## 可复用规则

1. 在 Windows 上用 PowerShell 改**任何** `*.json`（尤其插件/配置文件），改完必须验首三字节；`Set-Content -Encoding UTF8`（PS 5.1）会加 BOM，用 `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))` 或 `write` 工具。
2. "插件在 DSH 里整体消失"的排查顺序：内核 `loadProfileDirectory` 的 `skippedBundles` → 文件字节（BOM）→ JSON 能否 parse → 再谈代码。
3. 别用"重启后还没好"当作代码有 bug 的证据：先证明 bundle 被组合进去了（条目数、`archived 条目`、`重复 id`）。
4. `cordis.patch.yml` 里查不到某个插件名，不等于它没配置——bundle patch 是另一层；手工往 profile patch 里补同一条会造成重复插入风险，先修 bundle 可读性。
5. GUI 启动时的 `stderr` 诊断没人看：任何"静默跳过"型诊断，都要有等价的离线复现脚本。

## 适用范围与不适用范围

- 适用：DSH 自定义插件（bundle patch 形式）、`package.json` 被 PowerShell/编辑器改过的场景、Electron asar 内的 `dsh-app-boot` 诊断。
- 不适用：官方 `@deepseek-ai/*` 包（安装时由 pnpm 写入，一般无 BOM）；`requirements` 版本不匹配导致的 skip（另一条 reason，需要版本豁免或升级）。

## 剩余风险

- 其它被 PowerShell 写过的插件配置文件可能仍带 BOM（本次只查了 `archived-cleanup` 的 4 个文件）。
- `dsh --profile desktop --dump-config` 不可用，离线诊断必须走 `loadProfileDirectory` 脚本，脚本与内核版本绑定（当前 0.2.2-rc.5 的 `app-boot` 导出 `loadProfileDirectory` / `composeEntries` / `readProfilePatches`）。

## 关联

- [[踩坑-DSH启动弹黑框等按键-守卫pause叠加遗留中间态目录]]
- [[踩坑-PowerShell写配置带UTF8BOM让Go程序静默读不到并一层掩盖一层]]
- [[规则-本地手册接入DSH成为默认前置与写Markdown的编码坑]]
