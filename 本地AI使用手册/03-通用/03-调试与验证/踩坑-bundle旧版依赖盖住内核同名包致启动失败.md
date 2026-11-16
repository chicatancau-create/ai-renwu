---
title: "第三方bundle的旧版依赖盖住内核同名包导致应用启动失败"
date: 2026-11-03
domain: common
category: 调试与验证
status: verified
severity: high
stack: [DeepSeek Harness, pnpm, Electron, Cordis, typert]
tags: [依赖遮蔽, 版本错配, 启动失败, 可逆处置]
---

# 问题：给 DSH 装 `dsh-super-agent@0.0.5` 后，重启应用直接 `DeepSeek Harness is unavailable`

## 一句话结论

**bundle 自带的依赖里带着 `@deepseek-ai/dsh-llm` 等一整套 0.1.2-rc.1，被 pnpm 装进 profile 的 `node_modules` 后盖住了内核自带的 0.2.1-rc.5**；旧版 `llm/discoverModels` 的参数 codec 没有 `create()` 工厂，`typert-loader`（必需插件）校验失败 ⇒ 宿主启动中止。这类故障**装的时候完全看不出来**（pnpm 回 `Done in 5s`、包文件齐全），只在**下一次冷启动**才爆。

## 触发条件与影响

- 项目或功能：DSH 桌面端 0.2.1-rc.5，profile `~\.dsh\profiles\desktop`
- 触发条件：`plugin_manager.install_bundle` 装了未与内核同版对齐的第三方 bundle
- 影响：**应用打不开**（窗口停在 "DeepSeek Harness is unavailable"），且现场极易误判成"我改坏了配置"
- 关键时间差：15:55 装包 → 内核 12:55 起就没重启，所以**装了没生效也没报错**；17:22 我第一次重启才引爆

## 复现步骤

1. 装 bundle：`pnpm` 日志回 `+ dsh-super-agent 0.0.5 / Done in 5s`，`resolved 16, downloaded 13, added 16`
2. 应用照常运行（因为内核是装包之前起的）
3. 重启应用 ⇒ 启动失败

## 证据（决定性对照）

```
profile node_modules/@deepseek-ai/（全部 mtime = 15:55，装包前这个目录不存在）
  dsh-llm 0.1.2-rc.1   dsh-agent-presets 0.1.2-rc.1   dsh-session 0.1.2-rc.1
  dsh-session-projection / dsh-typert-protocol / dsh-brand / dsh-timeout
  dsh-util-crypto / dsh-util-values 0.1.2-rc.1        cosmokit 1.8.6   schemastery 3.18.5

内核 app.asar 内同包版本
  dsh-llm 0.2.1-rc.5   dsh-typert-loader 0.2.1-rc.5   cordis 4.0.5   schemastery 3.18.5
  且 `dsh-agent-presets` 在 asar 里出现 0 次（bundle 补丁要挂的那个服务，本机内核根本没有）

崩溃日志 %APPDATA%\@deepseek-ai\dsh-desktop\logs\crash-*-host.log
  DesktopHostFatalError: dsh: startup failed: 1 required plugin did not activate
    Failed plugins (1): typert-loader
      @deepseek-ai/dsh-llm invocation "@deepseek-ai/dsh-llm#llm/discoverModels"
      parameter codec has no create() factory
  另有 43 个插件停在 "waiting for services"（sessions/sessionProjections 等全被拖住）
```

**排除过程（每一步都只改一个变量并重启验证）**：

| 试的假设 | 动作 | 结果 |
|---|---|---|
| 我写的 4 行 preset 提前加载了新插件导致失败 | 回滚 `cordis.patch.yml` 到备份（611→399 行） | 同一错误 ❌ 假设不成立 |
| bundle 本体被加载导致失败 | 从 `package.json` 的 `bundles` 里摘掉 `dsh-super-agent` | 同一错误 ❌ 假设不成立 |
| profile 里的旧版 `@deepseek-ai/*` 遮蔽内核 | 把 `node_modules/@deepseek-ai` 与 `node_modules/dsh-super-agent` **改名移出**（可回滚） | **启动成功 ✅ 窗口回到「杂事处理 — DeepSeek Harness」** |

## 根因分析

- 已确认的根因：bundle 的依赖未与宿主内核版本对齐，包管理器把**同名旧版**装进了 profile 的解析路径，遮蔽了宿主自带版本。
- 为什么装的时候没报错：内核是**装包之前**启动的，新包从未被加载；pnpm 只校验自己的解析，不校验与宿主的版本一致性。
- 为什么极易误判：报错文案只提 `dsh-llm` 的 codec，不提是谁把旧版 `dsh-llm` 放进来的；而现场能看到的"最近改动"是别人的配置文件。
- 问题归属：第三方 bundle 的依赖声明 + 宿主允许 profile 级遮蔽解析；**不是**本次改的 preset 配置。

## 最小修复（已执行）

1. `node_modules/@deepseek-ai` 与 `node_modules/dsh-super-agent` **移到会话证据目录暂存**（不删，可原样放回）。
2. `package.json`：`dsh.profile.bundles` 去掉 `dsh-super-agent`，**`dependencies` 清空为 `{}`** —— 这一步是关键，
   只摘 bundles 不摘 dependencies 的话，任何一次 `pnpm install` 都会把旧包重新拉回来再炸一次。
3. 回滚我加的 4 行 preset（那批预设本来就依赖被遮蔽的 `dsh-agent-presets` 服务）。
4. `pnpm-lock.yaml` 保持原样（`corepack pnpm` 是 12.5.1、DSH 自带 11.28.5，
   只跑 `--lockfile-only` 确认它回 "Already up to date" 且 `lockfileVersion: '9.0'` 未被升级——**别用不同大版本的 pnpm 重写宿主的 lockfile**）。

## 验证记录

- [x] 三次单变量重启，逐条排除（回滚补丁 / 摘 bundle / 移旧包）
- [x] 移旧包后启动成功，窗口恢复会话标题
- [x] 最后一次 crash 停在 17:28:35，之后无新崩溃
- [x] `dependencies` 已清空、`bundles` 不含该包、`node_modules/@deepseek-ai` 不存在
- [ ] 未再做一次"干净冷启动"验证（当前配置比 17:28 成功启动时更保守，不为验证再折腾一次停机）

## 追加（同日）：最终修好了——钉版本，而且钉的位置不是 package.json

用户选了「试钉版本」。关键两点：

1. **registry 上有内核同版**：`@deepseek-ai/dsh-llm` 等 42 个版本里 `next` 就是 `0.2.1-rc.5`，
   `dsh-session / dsh-session-projection / dsh-brand / dsh-timeout / dsh-typert-protocol /
   dsh-util-crypto / dsh-util-values` 同样有 `0.2.1-rc.5`，`cordis 4.0.5`、`schemastery 3.18.5`、
   `cosmokit 1.8.6` 都在。**先逐个查版本再动手**——我第一版查询脚本写错过一次，
   得出「registry 没有」的错误结论，差点放弃可行方案。
2. **`pnpm.overrides` 写在 `package.json` 里会被静默忽略**。pnpm 11 的警告原文：
   `The "pnpm" field in package.json is no longer read by pnpm. The following keys were ignored: "pnpm.overrides"`
   ⇒ 设置必须写进 **`pnpm-workspace.yaml`** 的 `overrides:` 段。写错位置时 install 只回
   `Already up to date`，版本一个都没变——**这种"成功但没生效"最容易骗人**，所以装完必须
   回读 `node_modules/@deepseek-ai/*/package.json` 的版本逐个比对，不能只看 rc=0。

执行与结果：

```
pnpm-workspace.yaml 加 overrides（11 项，钉到内核同版）
corepack pnpm@11.28.5 install        → Packages: +12, downloaded 9, added 12, Done in 13.2s
复核 node_modules/@deepseek-ai/*     → 11 项全部 OK，未对齐: 无
冷启动 DSH                            → 无 crash，窗口恢复「杂事处理 — DeepSeek Harness」
再按内核 schema 补 4 行 @deepseek-ai/dsh-agent-preset → 又一次冷启动，仍无 crash
```

两个必须记住的口径：

- **用宿主应用自带的 pnpm 大版本**（DSH 用 11.28.5）。我用 corepack 默认的 12.5.1 试过一次，
  它回 "Already up to date" 没改 lockfile，但**跨大版本重写 lockfile 会让宿主自己的安装路径失配**，
  所以先确认 `lockfileVersion` 没被改动再继续。
- **profile 是 `nodeLinker: hoisted`**，这就是遮蔽能发生的结构性原因：扁平目录里的同名包会优先于宿主内置包被解析。

仍未证实（截至本条日期）：四个预设是否真的进了名册。网关路由要鉴权（`/` 回 401、`/api/presets` 回 403），
运行时日志里也没有 preset 记录，所以只能靠 UI 的预设下拉确认。**「补丁语法正确 + 启动不报错」不等于「服务已注册」**——
Cordis 对不上号的行是静默跳过的。

## 可复用规则

- **给宿主应用装第三方 bundle/插件前，先看它的 `dependencies` 里有没有与宿主同名的包**；有就别装，或先确认版本与宿主一致。
- 装完立刻做**遮蔽检查**：列 profile/工作区 `node_modules` 里与宿主内置包同名的目录并比对版本，别等下次冷启动。
- 宿主"装完没事、重启才炸"是常态 ⇒ **装插件后主动做一次冷启动验证**，并且要在**能接受停机的时候**做。
- 排障时**一次只改一个变量并重启**；本轮三次重启就把"配置问题"和"依赖遮蔽"分开了。
- 崩溃日志位置：`%APPDATA%\<宿主>\logs\crash-*-host.log`（含 `Failed plugins` 与 `waiting for services` 全表，比 UI 上的错误有用得多）。

## 适用范围与不适用范围

- 适用：任何"宿主内置插件 + 用户目录可再装同名包"的运行时（DSH、VS Code 扩展、Obsidian 插件、Electron 应用插件体系）
- 不适用：纯 CLI 工具链（没有常驻宿主，遮蔽只影响当次命令，报错当场可见）

## 剩余风险

- 被隔离的旧包只是移出，**没有回写 lockfile**；若将来有人把 `dsh-super-agent` 重新加进 `dependencies`，同样的遮蔽会复发。
- 该 bundle 在本内核上不可用，直到作者把依赖对齐到 0.2.1-rc.5 线；四个预设（solo/team/research/optimization）因此**暂时拿不到**，不是配置没写。
- 本次为验证做了 3 次冷启动，其中一次把用户正在用的会话 turn 打断（该 turn 此前已 60 分钟无落盘，判定为僵死）。

## 关联

- 相关记录：[[踩坑-会话进行中装插件致热重载报service-unavailable]]（同一 bundle、同一条排查线）、
  [[规则-Electron的app.asar可直接按头解析取文件无需asarCLI]]（本次对照内核版本就是靠直接解析 asar 头做的）、
  [[踩坑-无权限读ProgramData被当成文件不存在致误删服务拆掉内核]]（同为"重启才暴露"的时序陷阱）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
