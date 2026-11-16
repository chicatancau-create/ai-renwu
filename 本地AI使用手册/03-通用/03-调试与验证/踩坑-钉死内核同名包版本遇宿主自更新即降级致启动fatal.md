---
title: "把依赖手工钉成「当时内核的版本」是定时炸弹：App 自更新后钉版过期，同名包被降级禁用、启动直接 fatal"
date: 2026-11-04
domain: common
category: 调试与验证
status: verified
severity: high
stack: [DeepSeek Harness desktop, Electron, pnpm 11, cordis]
tags: [版本钉死, 内核自更新, 插件禁用, overrides, Authenticode, 升级流程]
---

# 问题：修「安装更新失败」修到一半，应用从"能跑"变成"起不来"

> 本条是 [[踩坑-bundle旧版依赖盖住内核同名包致启动失败]] 的**下半场**：
> 昨天用 overrides 把同名包钉到内核版本修好了，今天内核一升级，那颗钉子反过来把应用钉死了。

## 一句话结论

**"钉到当前内核版本"这种修复必须带一个到期日**：宿主 App 一旦自更新，钉版就从"对齐"变成"降级"，
被钉的那个插件会**静默 disabled**，于是一串服务没人提供、required 插件起不来、启动 fatal。
所以钉版之后要做的是**记下"内核升级即失效"**，并在每次升级后从**新内核自己带的包**里重新读版本对齐。

## 触发条件与影响

- 软件：DeepSeek Harness 桌面端（Electron 44.7 / node 24.21 / pnpm 11.28.5）
- 路径：安装 `D:\DeepSeek Harness`，profile `C:\Users\Admin\.dsh\profiles\desktop`
- 事件链：
  1. 界面弹「安装更新失败，请稍后重试。」技术详情 `desktop update: task inspection timed out`（18:22）
  2. 我核完包直接装：0.2.1-rc.5 → **0.2.2-rc.1**，装完重启 → **启动 fatal**（20:57 两份 crash 日志）
  3. 真因：profile 的 `pnpm-workspace.yaml` 里还钉着 `@deepseek-ai/dsh-*: 0.2.1-rc.5`、
     `cordis 4.0.5 / schemastery 3.18.5 / cosmokit 1.8.6`
- 影响面：应用完全打不开（比原来的"更新没装上"严重得多）

## 复现步骤

1. 前置：为修 bundle 遮蔽，把若干 `@deepseek-ai/*` 用 pnpm `overrides` 钉成当时内核的版本
2. 操作：让宿主 App 自更新到新版本（本例 nightly 0.2.1-rc.5 → 0.2.2-rc.1）
3. 预期：内核与 profile 依赖一起前进
4. 实际：profile 仍解析出旧版 ⇒ 崩溃日志里**只有那一个插件是旧版且 `state:"disabled"`**：
   ```
   {"id":"include:session","module":"@deepseek-ai/dsh-session","version":"0.2.1-rc.5","state":"disabled"}
   （其余插件全是 0.2.2-rc.1 / active）
   DesktopHostFatalError: dsh: startup failed: 1 required plugin did not activate
   Plugins waiting for services (56): agent-loop (required) → agents, sessions, sessionProjections …
   ```

## 证据

| 取证 | 结果 |
|---|---|
| 更新为何"超时" | `pending` 里最终有 293,425,336 B 完整安装包（mtime 19:31，即 18:22 失败后重试下载成功）⇒ 超时是**大包下载慢**，不是源坏了 |
| 包完整性 | 实计算 SHA512 `swcK0J6ofGkaAWLRpOes2ca7…` 与 `update-info.json` 声明**完全一致** |
| 包来源可信 | `Get-AuthenticodeSignature` = Valid，GlobalSign **EV** 代码签名，主体序列号 `91330105MACPN4X08Y` **与已装 exe 同一个**，DigiCert 时间戳 |
| 更新配置 | `resources/app-update.yml`：provider generic、`https://download.deepseek.com/dsh-desk/feeds/win-x64/`、channel nightly |
| 装前是否安全 | 6 个进程 8 秒 ΔCPU 全 ≤0.06s、`~/.dsh` 近 10 分钟零落盘 ⇒ 空闲，可安全重启 |
| 内核自带版本 | 直接读 `app.asar` 内 `node_modules/@deepseek-ai/*/package.json`：`cordis 4.1.0`、`schemastery 3.19.0`、`cosmokit 1.9.0`、`dsh-brand/timeout/typert-protocol 0.2.2-rc.1` |
| 钉版是否过期 | profile `node_modules` 实测：`dsh-* 0.2.1-rc.5`、`cosmokit 1.8.6`、`schemastery 3.18.5` ⇒ 全部落后 |
| 版本可得性 | npmmirror 上 11 个目标版本**都存在**（`next` tag 就是 0.2.2-rc.1） |

## 根因分析

- 已确认根因：**overrides 写死了具体版本号**，宿主升级后不再等于内核版本，反而把内核同名包降级并禁用。
- 排除过的假设：①"更新包没下全"——SHA512 匹配，否；②"新内核不兼容旧 profile 数据"——
  崩溃信息精确指向单个旧版插件，否；③"是 `dsh-super-agent` 又遮蔽了"——它的 `dsh-agent-presets 0.1.2-rc.1`
  仍在但插件状态 active，不是本次致命点。
- 问题归属：**本次修改引入**（昨天的钉法）+ 触发条件是宿主自更新（不可避免）

## 最小修复

**A. 把更新装上（这次的部分诉求）**

```powershell
# 先验包：哈希 + 签名，两者都过再动
taskkill /F /IM "DeepSeek Harness.exe"          # 空闲时才做
& "<pending>\deepseek-harness-0.2.2-rc.1-win-x64.exe" /S     # 退出码 0，25 秒
```

**B. 钉版对齐到新内核（真正的修复）**

`pnpm-workspace.yaml` 的 overrides 改成内核自带版本，然后重装：

```
'@deepseek-ai/dsh-llm|dsh-session|dsh-session-projection|dsh-brand|dsh-timeout|
 dsh-typert-protocol|dsh-util-crypto|dsh-util-values': 0.2.2-rc.1
'@deepseek-ai/cordis': 4.1.0
'@deepseek-ai/schemastery': 3.19.0
'@deepseek-ai/cosmokit': 1.9.0
```

```bat
cd C:\Users\Admin\.dsh\profiles\desktop
cmd /c corepack pnpm@11.28.5 install --no-frozen-lockfile
```

> 两个本机固定坑仍在：`overrides` 必须写在 **pnpm-workspace.yaml**（package.json 的 pnpm 段被 pnpm 11 忽略）；
> pnpm 版本要跟内核一致（corepack 默认 12.5.1 ≠ 内核的 11.28.5）。

## 验证记录

- [x] 版本：`FileVersion` 0.2.1-rc.5 → **0.2.2-rc.1**，安装器退出码 0
- [x] 对齐后 profile `node_modules` 实测 11 个包全部到位，`仍是旧版的包 = 无`
- [x] 冷启动：5 进程、主窗口标题「杂事处理 — DeepSeek Harness」（会话页渲染出来才算起来），
      crash 目录**无新日志**（最新仍是失败的 20:57 那两份）
- [x] 昨天的成果没丢：`cordis.patch.yml` 621 行、5 处预设声明、两处 `input: [ text, image ]` 都在
      （注意它写成带内空格的形式，用 `input:\s*\[text, image\]` 去搜会假报"0 处"）
- [x] 垃圾清理：用尽的 293 MB 安装包删除前确认版本已装，删后 `pending` 只剩 blockmap 与 update-info

## 可复用规则

1. **凡是"钉到宿主当前版本"的修复，落笔时在旁边写清失效条件**：`# 内核升级即需重新对齐`。
   更好的做法是能不钉就不钉，或钉成范围（`^0.2.2`）而非精确值。
2. **升级宿主后，先读新宿主自带的版本再动 overrides**：Electron 应用直接解析
   `resources/app.asar` 里 `node_modules/<pkg>/package.json`，这是唯一可信的"内核版本"。
3. **判"插件为何没激活"看崩溃日志的插件清单**：找**版本号与同批不一致**、且 `state` 不是 active 的那一行，
   比读 56 行"waiting for services"快得多。
4. **装更新前的三道闸**：①包哈希与服务器声明一致；②Authenticode Valid 且**主体与已装 exe 同一序列号**；
   ③确认应用空闲（ΔCPU + 近期无落盘）。三道过了才 `taskkill` + `/S`。
5. **"安装超时"先查 `pending` 目录**：包是否已下完、大小/哈希对不对——多数是慢，不是坏。

## 适用范围与不适用范围

- 适用：任何"宿主 App 自带一套包 + 用户 profile 可再装包"的结构（DSH、WorkBuddy、VS Code 扩展宿主、
  各类 plugin-runtime），以及一切用 overrides/resolutions 压制传递依赖的场景
- 不适用：锁文件完全由宿主管理、用户无法覆盖依赖的结构
- 例外：若 profile 与内核版本天然同步（同一构建产物），钉版不会失效

## 剩余风险

- **下次内核再升级（0.2.2-rc.1 → 更高），这条会原样复发**。要根治得把 overrides 改成范围或去掉，
  但去掉后 `dsh-super-agent@0.0.5` 的旧依赖又会回来遮蔽（昨天的病），所以当前是两害相权的解。
- `dsh-agent-presets` 仍是 `0.1.2-rc.1`（super-agent 带的），本次未受影响，但属同类隐患。
- 更新走 nightly channel，包体积 293 MB，超时提示可能反复出现。

## 关联

- 相关记录：[[踩坑-bundle旧版依赖盖住内核同名包致启动失败]]（本条的上半场）、
  [[踩坑-会话进行中装插件致热重载报service-unavailable]]、
  [[踩坑-App自更新后手动重装服务会装旧二进制且卸载器删内核致静默降级Sidecar]]（同一族：宿主自更新让手工对齐过期）
- 相关分类：03-通用/03-调试与验证
- 本机产物：`02_证据日志\repins-20261104\`（改前 pnpm-workspace/package/lock/cordis 五份）、
  `03_工具脚本\{read_kernel_deps,repin_dsh_profile,apply_dsh_update}.py`、`%TEMP%\dsh_repins.txt`
