---
title: "给 DSH 装/卸插件：命令行给 scoped 包名加引号会被 pnpm 当成垃圾别名；dsh plugin add 会自己登记 bundles；桌面 profile 不能 --dump-config"
date: 2026-11-07
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [DeepSeek Harness, pnpm 11.28.5, cordis, Windows 11]
tags: [DSH, 插件安装, bundles, provider, scoped 包, 引号, asar 取证]
---

# 经验：DSH 的插件装卸与 provider 删除，四个动作点

## 一句话结论

给 DSH 装插件唯一正确入口是 `dsh plugin --profile desktop add <包名>`（它内部转发 pnpm），
但**包名一律不要加引号**——`dsh.cmd` 会再包一层，cmd 把引号烤进参数，pnpm 就把它当"非法别名"：
`plugin"` / `memsearch-dsh"` 这样的垃圾键直接写进 `package.json`，还得手工清。
装完 `add` 会**自己把包追加进 `dsh.profile.bundles`**（不是只写 dependencies）；
`--dump-config` 在 desktop profile 上会被拒（`profile "desktop" is managed exclusively by the Electron application`），
所以验证只能靠重启 GUI 后看「插件 → 已安装插件」列表。

## 触发条件与影响

- 环境：DeepSeek Harness 内核 0.2.2-rc.1，profile `~/.dsh/profiles/desktop`，pnpm 11.28.5。
- 触发条件：用 CLI 批量装带 scope 的插件（`@dsh-market/plugin`、`@zilliz/memsearch-dsh`），且习惯性加引号。
- 影响：`package.json` 出现 `"plugin\"": "link:\"@dsh-market/plugin\""` 这类键，pnpm 报
  `ERR_PNPM_INVALID_DEPENDENCY_NAME ... invalid alias "memsearch-dsh\""`，**整条 add 命令失败**；
  但**已解析的依赖已经落盘**，所以状态是"三个装上了、两个没装上、还有两个垃圾键"的混合态。

## 复现步骤

1. `cmd /c "dsh.cmd plugin --profile desktop add \"@dsh-market/plugin\" dsh-better-sidebar ..."`
2. 预期：五个都装好。
3. 实际：`[WARN] Installing a dependency from a non-existent directory: ...\desktop\"@dsh-market\plugin"`；
   结尾 `ERR_PNPM_INVALID_DEPENDENCY_NAME ... invalid alias "memsearch-dsh\""`；
   `package.json` 里多出 `plugin"` / `memsearch-dsh"` 两个键，`node_modules` 里却已经铺了 247 个包。

## 证据

- `02_证据日志\candidate_packages.json`：九个候选包的 `dsh.bundle.patch`、`@deepseek-ai/*` 依赖范围。
- 失败现场（当时 package.json 片段）：
  `"memsearch-dsh\"": "link:\"@zilliz/memsearch-dsh\"", "plugin\"": "link:\"@dsh-market/plugin\""`
- 修好后 `.plugin-manager\logs\operation-*\pnpm.log`：
  `+ @dsh-market/plugin 0.4.17 / + @zilliz/memsearch-dsh 0.1.8 / + billion-context 0.1.212 / + dsh-better-sidebar 0.30.1 / + dsh-context 0.82.0`
- GUI 取证：`02_证据日志\插件页-已安装.png`（截图见下方"验证记录"），五项都在且开关为开。

## 根因分析

- 已确认：`dsh.cmd` 是把参数原样转给 pnpm 的批处理包装，自己会再加引号；
  我多包的一层引号没被 cmd 的引号规则吃掉，而是**作为字面字符**进了 pnpm 的 spec。
- 排除：不是网络问题（同一轮里 247 个包都下载成功了）；不是权限；不是内核版本。
- 归属：**我的操作方式**。

## 最小修复

1. 从 `package.json` 删掉带引号的垃圾键（两个），保留三个已装好的。
2. 重跑一次**不带引号**：`dsh plugin --profile desktop add @dsh-market/plugin @zilliz/memsearch-dsh` → 成功。
3. 把五个包按加载顺序归一到 `dsh.profile.bundles`（`@local/dsh-preset-switcher` 放最后）：
   `base → web-app → experimental×4 → dsh-better-sidebar → dsh-context → billion-context → @dsh-market/plugin → @zilliz/memsearch-dsh → dsh-super-agent → @local/dsh-preset-switcher`
4. 重启 GUI 才生效（`D:\DSH-Guard\start_dsh.bat`，守卫先对齐内核版本再起 exe，实测 rc=0）。

## 验证记录

- [x] YAML/JSON 静态：`cordis.patch.yml` 用 SafeLoader（额外注册 `!!js` 构造器）解析通过，顶层条目 15 → 14（只少了 `llm-pi-ai`）
- [x] 装完 `dsh plugin list` 五个包齐全；`dsh_kernel_sync.py` rc=0（overrides 与 node_modules 仍对齐）
- [x] 关应用前后 `cordis.patch.yml` / `package.json` 的 SHA256 不变（证明退出时不会覆盖我的改动）
- [x] GUI 重启后「插件 → 已安装插件」五项全部在列且开关为开：Better Sidebar / billion-context / 上下文(dsh-context) / @zilliz/memsearch-dsh / @dsh-market/plugin
- [x] 左栏出现「插件市场」「上下文洞察」；输入框上方出现「MemSearch 0」入口
- [x] 模型选择器变成 `DeepSeek-V4.1-Flash xhigh`，WorkBuddy 系列全部消失
- [ ] 未验证：没有替他发一轮真实模型请求去证明"Provider finish_reason: error"彻底消失（会消耗他的额度）

## 可复用规则

1. **给 DSH 装插件**：`dsh plugin --profile desktop add <包名>`，**包名不加引号**；带 scope 的也一样。
2. **判断一个 npm 包能不能装进 DSH**：看它的 `package.json` 里有没有 `dsh.bundle.patch`；
   再比 `@deepseek-ai/*` 依赖区间是否包含本机内核版本（本机 0.2.2-rc.1）。本轮实测：
   `billion-context-dsh` 要求 `dsh-llm <0.2.1-0` ⇒ 不能装；`billion-context`（无宿主依赖）才是对的；
   `dsh-memsearch` 无 `dsh` 字段且依赖旧版 `dsh-agent` ⇒ 改用 `@zilliz/memsearch-dsh`。
3. **桌面 profile 不能 `--dump-config`**（被 Electron 独占），验证只能重启 GUI 看插件页；
   `dsh plugin --profile desktop list` 是可以用的。
4. **删一个 provider 插件**：它多半只是 `cordis.patch.yml` 里的一段 `@deepseek-ai/dsh-llm-pi-ai` 配置，
   删掉整段，再把 `agent-default-model` 与 `subagent-model-selection-settings.allowedModels` 指回官方。
   官方账号 provider id = `deepseek-account`，模型 `deepseek-flash`（显示名 DeepSeek-V4.1-Flash）/ `deepseek-v4-pro`。
5. 改 `cordis.patch.yml` 前先备份；改完用 SafeLoader + `!!js` 构造器解析一遍；关闭应用后再比对 SHA256，
   确认应用退出时没有用内存里的旧配置覆盖文件。

## 适用范围与不适用范围

- 适用：DSH（DeepSeek Harness）桌面端、cordis 体系插件；pnpm 转发式 CLI 包装。
- 不适用：TUI/web profile（那两种可以 `--dump-config` 自检）；不是 DSH 的普通 npm 项目（`dsh.bundle` 字段无意义）。

## 本机痕迹

- 备份：`G:\AIrenwu\2026-11-07_DSH插件\02_证据日志\改前留档\{cordis.patch.yml.*.bak, profile-before-plugins\, workbuddy-artifacts\}`
- 脚本：`G:\AIrenwu\2026-11-07_DSH插件\03_工具脚本\{remove_workbuddy, check_candidates, asar_provider_scan, asar_extract_llm_deepseek, close_dsh, click_plugins_page}.py|.ps1`
- 被删的 WorkBuddy 痕迹：`~/.dsh/.workbuddy-*.json` 六个文件已移入上面的 `workbuddy-artifacts`；
  `.credentials.yaml` 里还留着 `WORKBUDDY_API_KEY`（未动，需要的话可一并清）。

## 2026-11-07 补：界面汉化、id 覆盖项会炸启动、memsearch 的依赖怎么选

**① 插件界面只有英文时怎么汉化**：像 `@zilliz/memsearch-dsh` 这种**没有 i18n 机制**的插件，
文案全硬编码在 `node_modules/<包>/client.js` 里。做法：逐条替换字符串 → `node --check` 校验 →
重启 GUI。要点：**只换用户可见串，别碰 URL / 类名 / 拼接变量**；复数拼接（`' item' + (n===1?'':'s')`）
整段换成中文，否则会出现“1 个候选技能s”。脚本 `G:\AIrenwu\2026-11-07_DSH插件\03_工具脚本\localize_memsearch.py`
是幂等的，**插件升级覆盖后重跑一次即可**（它同时把 `summarizeEnabled: false` 写回 bundle patch）。

**② `cordis.patch.yml` 里只写 `- id: xxx` 不带 `name` 会炸启动**：我按文档“id-targeted override”
加了一条 `- id: memsearch / config: {summarizeEnabled: false}`，结果应用起不来：
`crash-host.log` 报 `dsh desktop host exited with 4294967295: dsh: warning: 1 entry did not activate`，
指向 `experimental-inspector: globalThis.fetch is an accessor and cannot be observed safely`，
而且**进程还在、窗口是 0 个**（`MainWindowHandle=0`）——很像“装好了但界面没出来”。
判据：先看 `%APPDATA%\@deepseek-ai\dsh-desktop\logs\crash-<utc>-host.log` 有没有比本次启动更新的文件；
回滚那条覆盖项后窗口立刻恢复。**正确做法：改插件自己的 `cordis.patch.yml`（带 id + name），
不要在用户层写裸 id 覆盖。**

**③ memsearch 装完不等于能用**，三个卡点都要过：
- CLI：`uv tool install "memsearch[onnx]"`（本机把 `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` 指到 D 盘，PATH 追加 `D:\uv\bin`）；
- 嵌入后端：默认是 **OpenAI**（要 key），必须 `memsearch config set embedding.provider onnx`，
  模型 `gpahal/bge-m3-onnx-int8`（约 561 MB，用 `HF_HOME`/`HF_ENDPOINT` 指到 D 盘与 hf-mirror）；
- 摘要：插件默认 `summarizeMode=auto` → 调 `dsh headless`，而 **headless 走 API key 路由**
  （实测 `MISSING_CREDENTIAL: ... provider route "deepseek-official"`）⇒ 每轮都会写一条“记忆不可用”。
  要么关掉摘要（原文写入，零调用），要么给 headless 配 key。
- 附带：面板“打开目录”按钮写死了 Linux 的 `xdg-open`，Windows 上只会回显路径。

**验证方法**：`memsearch index <dir>` 应回 `Indexed N chunks`，`memsearch search "<中文问题>"` 能命中；
插件侧的落盘位置是 `<项目目录>\.memsearch\memory\日期.md`。
