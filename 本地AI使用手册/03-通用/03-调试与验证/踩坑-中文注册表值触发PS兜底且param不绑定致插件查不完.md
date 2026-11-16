---
title: "插件在中文 Windows 上的注册表兜底因 param 无法绑定而必然失败"
date: 2026-10-12
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: high
stack: [PowerShell 5.1, Node.js, Windows Registry, DSH, dsh-workbuddy-connect]
tags: [环境相关bug, 中文系统, 判据]
---

# 问题：DSH 的 `dsh-workbuddy-connect` 报 "the WorkBuddy AI application search did not finish … not proof that the app is missing"

## 一句话结论

不是 App 没装，也不是超时。**插件的注册表兜底脚本用 `powershell -Command "param([string]$Root) …" -Root <根>` 调用，
PowerShell 5.1 不会把命令串后面的 `-Root x` 绑定给 `param()`**，于是 `$Root` 恒为空、
`Get-Item "Registry::"` 抛错、脚本 `exit 3`（`root unreadable`）→ 插件判"查不完"。
而**只有当 `reg.exe` 输出含非 ASCII 字节时才会走这条兜底**——中文软件名（阿里云盘、哔哩哔哩、
Visual Studio 生成工具）正好触发，所以这 bug 只在中文 Windows 上出现，英文系统永远碰不到。

## 触发条件与影响

- 环境与版本：Win11 28000 + PowerShell 5.1.28000.2952（FullLanguage，执行策略 Restricted 但 `-Command` 不受影响）+
  DSH 0.2.0-rc.2 + `dsh-workbuddy-connect` **0.7.2**。
- 触发条件：卸载项注册表里存在任何非 ASCII 的 `DisplayName`。
- 影响范围：WorkBuddy / WorkBuddy AI **两个产品分组都出不来**，模型选择器里整组消失；与登录状态无关。

## 复现步骤

1. 前置条件：中文 Windows，装了 WorkBuddy（本例两版都在 `D:\WorkBuddyAIguonei`、`D:\WorkBuddyAIgouji`）。
2. 操作或命令：原样跑插件的兜底脚本（脚本正文从 bundle 抽出，未改写）：
   `powershell -NoProfile -NonInteractive -Command "<插件那段 param([string]$Root)…>" -Root "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall"`
3. 预期结果：输出该根的 JSON。
4. 实际结果：**退出码 3，stderr `root unreadable`，stdout 0 字节**，三个根全一样（各 ~1.2s，串行合计 3.5–4.0s）。

## 证据

- `reg.exe` 输出实测：HKCU 29194B / HKLM 154977B / WOW6432Node 172012B，**三者都含 GBK 非 ASCII 字节**
  （`\xb0\xa2\xc0\xef\xd4\xc6\xc5\xcc`=阿里云盘、`\xdf\xd9\xc1\xa8`=哔哩哔哩、`\xc9\xfa\xb3\xc9\xb9\xa4\xbe\xdf`=生成工具）
  → 插件的 `isAsciiOnly()` 为假 → 必走兜底。
- 用**插件自己的** `parseWindowsRegistryOutput` 跑真实 reg 输出：`incomplete:false`，
  候选正确解出 `D:\WorkBuddyAIguonei\WorkBuddy.exe` 与 `D:\WorkBuddyAIgouji\WorkBuddyAI.exe`
  → **解析与候选校验都没问题**，锅在取数环节。
- `param()` 绑定测试：`-Command 'param([string]$Root); …' -Root HKLM\Software` → PowerShell 直接报解析错
  （错误位置指向被追加到命令串尾部的 `-Root`）。
- 空 `$Root` 行为：`$path="Registry::"` → `Test-Path=True` 但 `Get-Item` 抛错 → 正是脚本的 `exit 3` 分支。
- 排除项：**路径写法不是原因**——`HKCU\…` 与 `HKEY_CURRENT_USER\…` 直接赋值给 `$Root` 都能 `Get-Item OK`（31 个子键）。
  也**不是超时**（单步上限 3s、整轮 10s，实测每步 1.2s）。
- 已有路径配置检查：`HKCU\Environment`（33 项）与机器级（21 项）里**从未有过** `WORKBUDDY_*` 变量。

## 根因分析

- 已确认的根因：兜底脚本的参数传递方式在 PowerShell 5.1 的 `-Command` 语义下不成立，`$Root` 永远为空。
- 排除过的假设：应用未安装（两版都在且布局合规）；`InstallLocation` 为空导致找不到（插件本来就读 `DisplayIcon`，不读 InstallLocation）；
  执行策略 Restricted（`-Command` 不受策略约束）；10 秒预算超时（实测远未触及）；注册表根路径写法。
- 问题归属：插件自身缺陷（第三方包），被中文环境触发。

## 最小修复

用插件自己预留的逃生口，**跳过整条 discovery**：`resolveElectronPath()` 第一句就是
`explicitPath = process.env[product.envVar]?.trim()`，命中即返回，只做可执行性检查。

```powershell
# 持久化到用户级（重启仍在），不是当前 shell 临时变量
[Environment]::SetEnvironmentVariable('WORKBUDDY_ELECTRON_BIN',    'D:\WorkBuddyAIguonei\WorkBuddy.exe',   'User')
[Environment]::SetEnvironmentVariable('WORKBUDDY_AI_ELECTRON_BIN', 'D:\WorkBuddyAIgouji\WorkBuddyAI.exe', 'User')
```

已在本机执行并回读一致。**必须完全退出并重启 DSH**（含托盘）——环境变量在进程启动时读取，
运行中的 DSH 不会热更新。

## 验证记录

- [x] 改前：兜底脚本对三个根全 `exit 3`（复现 3 轮一致）。
- [x] 两个 exe 存在、可执行、且 `version` + `resources\app.asar` 布局符合插件要求。
- [x] 环境变量写入 `HKCU\Environment` 并回读：两个值均 OK；已广播 `WM_SETTINGCHANGE`。
- [ ] **DSH 重启后模型分组是否出现：未验证**（需用户重启，未擅自杀其 5 个进程）。
- [ ] 未测：把变量指向错误 exe 时插件的 `electron-path-invalid` 分支。

## 可复用规则

第三方插件报"搜索没跑完 / 无法确定"时，**先按它的分支条件复现取数环节**，别接受"可能没装"这种结论：
① 用 bundle 里**它自己的解析函数**跑真实数据（本次证明解析是好的）；
② 再单独跑它的兜底子进程并看退出码语义（本例 `exit 3` 才是真凶）；
③ 判定"环境相关"的开关：本例是 `isAsciiOnly()`——**中文/日文等含非 ASCII 的系统会走与英文系统完全不同的代码路径**，
这是"别人能用我不能用"类问题的高频根因，优先查。

## 适用范围与不适用范围

- 适用：任何"只在中文 Windows 上失败"的 Node/Electron 工具，尤其是把 `reg.exe` 文本当主路径、
  把 PowerShell 当兜底的插件。
- 不适用：真正的 App 未安装（那会报 `electron-binary-not-found`，措辞不同且会说明候选被拒数量）。

## 剩余风险

环境变量是**写死的路径**：WorkBuddy 自动升级若换了安装目录或版本号目录，路径会失效
（届时报 `electron-path-invalid`，比现在的"查不完"更好懂）。彻底修法是上游把兜底改成
`-File`/`$args` 传参，或按控制台代码页解码 `reg.exe` 输出；本机也可打补丁，但插件更新会覆盖。

## 2026-10-19 复核：上面「剩余风险」预言的失效真的发生了，且判恢复的方法升级了

WorkBuddy 于 2026-10-15 10:04 升级后，国内版从 `D:\WorkBuddyAIguonei\` 搬进了 `D:\WorkBuddyAIgouji\WorkBuddy.exe`
（旧目录只剩 `debug.log` + `version` 两个残留文件，0 个 exe），于是本条当初设的 `WORKBUDDY_ELECTRON_BIN`
变成死路径，报 `the configured WorkBuddy Electron binary is not available at …`。

**定位与修复（照做可复现）**：
① 权威落点看**卸载注册表的 `DisplayIcon`**，不看目录名猜：
`HKCU\...\Uninstall` 里 `WorkBuddy 5.8.3` → `DisplayIcon=D:\WorkBuddyAIgouji\WorkBuddy.exe,0`（去掉 `,0` 即真路径），
`InstallLocation` 是空的，别指望它；② 改 `HKCU\Environment` 后广播 `WM_SETTINGCHANGE`（`SendMessageTimeoutW`，实测返回 1）；
③ 显式路径优先于自动探测，所以这一步必然生效，不受本条主案那个 PS 兜底 bug 影响。

**判"插件恢复没有"不要看界面文案，看插件自己落盘的账本**（这是本条新增的最硬判据）：

| 文件 | 含义 | 本次读到的 |
|---|---|---|
| `~\.dsh\.workbuddy-catalog.json` | 国内版模型目录缓存，含 `source` 与 `fetchedAtMs` | mtime 停在 10-15 08:54、`source=workbuddy:cli` → 升级后再没成功过 |
| `~\.dsh\.workbuddy-ai-catalog.json` | 国际版同上 | mtime 10-18 21:13、`source=workbuddy-ai:app` → 国际版一直是好的 |
| `~\.dsh\.workbuddy-probe.json` | 国内版探测记录 | **不存在**（对照：ai 的那份在） |
| `~\.dsh\.workbuddy-host-heartbeat.json` | 宿主心跳，带 `pid`/`pluginVersion` | 10-18 21:02、pid 52776（现已无此进程） |

⇒ 恢复成功的硬判据 = 国内版那份 catalog 的 **mtime 变成当天**且 `source` 由 `workbuddy:cli` 变成 `workbuddy:app`。
`source` 字段本身就是"有没有真的用上桌面 App"的证据，比任何提示文案可信。
> **⚠ 2026-10-19 更正：上面这条判据对国内版是错的，别照用。** 插件 README 明写
> 「国际版的模型目录来自 App 界面接口……**国内版目录走官方 CLI 同款接口，不受此影响**」，
> 所以国内版 `source=workbuddy:cli` **就是正常来源**，不是降级、不是没走 App。
> 两版正确的判据不同：**mtime 是否更新**（两版通用）+ 国际版才看 `source` 是否为 `workbuddy-ai:app`；
> 国内版要判死活看**卡片状态页的账号/令牌有效期**，以及 `~\.dsh\.workbuddy-auth.json`（插件自留凭据副本）在不在——
> README：某版 App 从未登录且没有自留副本时，**该版模型分组直接不显示**。

**2026-10-19 已实跑验证：自动探测在本机是通的，但贴着超时线跑。**
做法：把 `lib/host-heartbeat-sjotAEdb.js` 整份复制到 TEMP，补一个只导出 `resolveDshHome()` 的
`@deepseek-ai/dsh-home-paths` 桩包（真包只在 DSH 的 asar 里，磁盘上没有，所以 `lib/bin.js doctor` 离线跑不了），
然后调用插件**自己的** `atRestKeyProviderFor(variant).resolveElectronPath()`。
⚠ 造路径必须用 `path.join`：反斜杠字面量会在「JSON→bash→Python→JS」这条链上被吃掉一层，
结果 `D:\WorkBuddy…` 变成 `D:WorkBuddy…`，本会话连错两次才发现（同 auto-memory 里的 `reference-windows-python-encoding` 那一族坑，不是本库笔记）。

| 配置 | workbuddy | workbuddy-ai |
|---|---|---|
| 两条变量都删（动态） | OK 7.2 s | OK 6.8 s |
| 都删、换探测顺序 | OK 7.0 s | OK 7.4 s |
| 两条都设（显式） | OK **0.0 s** | OK **0.0 s** |
| 只设一条 | 另一条 OK 7.8 s | 另一条 OK 9.1 s |

**根因升级（覆盖本条主案的旧解释）**：`discoveryBudgetMs = options.discoveryBudgetMs ?? 1e4`，
即**每次探测预算 10 秒**，而本机动态探测实测要 **7–9 秒**，余量不足 30% —— 机器一忙（并发下载、别的会话在跑）
就超时抛 `the … application search did not finish`。所以 10-12 那次「查不完」不只是 PS 兜底脚本的锅，
**探测本身慢是同一症状的另一半成因**。新增判据：报这句时看耗时，接近 10 s 即预算被打满，不是 App 没装。

**本机最终选择**：删掉两条变量走动态（升级换目录不会再坏），代价是冷启动多花 7–9 s × 2。
若又报 `search did not finish`，用**从注册表现算**的命令加回来（路径不可能写错）：

```powershell
$cn = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' |
       Where-Object DisplayName -match '^WorkBuddy \d').DisplayIcon -replace ',0$',''
[Environment]::SetEnvironmentVariable('WORKBUDDY_ELECTRON_BIN', $cn, 'User')
```

## 2026-10-19 终局：两层根因都不是插件（启动器继承 + 网卡 DNS 写死）

1. **删了注册表环境变量还报错** → 值在**长命启动器的进程环境块**里（本机 `DeskBox.exe` 拉起 DSH），
重启被它拉起的程序无效。取证法：`OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ)` →
`NtQueryInformationProcess(class 0)` 拿 PEB → `PEB+0x20` 取 ProcessParameters → `+0x80` 取 Environment 指针 →
读固定长度按 `\0` 分隔切；**别信 `EnvironmentSize`（偏移取错会读到 0，害你误判"环境块是空的"）**。
附带一条：从自己的 shell 重启目标程序时 shell 本身也带旧值，必须显式剔除再传 env。
2. **`catalog.error="fetch failed"` 的真因是 DNS**：网卡 DNS 被写死 `1.1.1.1,8.8.8.8`
（`Get-NetIPInterface.Dhcp=Enabled` 会误导，接口注册表里有 `NameServer` 就是手动值、优先于 DHCP 下发），
国内域名 `www.codebuddy.cn` 冷解析 11.15 s 且被指到海外节点。改 `223.5.5.5,119.29.29.29` 后 0.13 s、解析回国内 IP。
**测域名必须分层计时（DNS/TCP/TLS/首字节）并先 `ipconfig /flushdns`**，否则第二次起全是缓存命中，
会把 11 秒的问题测成 0 秒——这正是这类"只在软件启动瞬间发作"的故障难复现的原因。
3. **不点 UI 也能读插件状态**：GET `http://127.0.0.1:<DSH监听口>/plugins/dsh-workbuddy-connect/{status|ai/status}`
（带 `Host`+`Origin`），返回 `status` / `catalog.source` / `catalog.error` / `visibility.disabled`。
4. 截图上「未登录」是**旧错误态**，接口实测 `status=signed-in` ⇒ 卡片文案滞后时以接口为准。

## 补充：2026-11-13 实测复核（路径与版本漂移）

- **WorkBuddy 安装路径再次漂移**：本记录所引国际版 `D:\WorkBuddyAIgouji\`（`WorkBuddy.exe` / `WorkBuddyAI.exe`）与旧国内版 `D:\WorkBuddyAIguonei\` 均已不存在（Test-Path MISS）。现役国内版为 `D:\WorkBuddyAI\WorkBuddy.exe`，FileVersion=**5.9.3**（与 [[规则-列表项累加先判派生视图再清源头数据]] 11-03 所载一致）。
- **自启项悬空（新发现，2026-11-13 已修复）**：HKCU `Run\WorkBuddy.WorkBuddyAI` 原指向 `"D:\WorkBuddyAIguonei\WorkBuddyAI.exe"`（死路径）⇒ WorkBuddy 自启实际失效。用户放行（「能修的就修」）后已改指 `"D:\WorkBuddyAI\WorkBuddy.exe"`（现役 5.9.3），`Set-ItemProperty` 后回读确认。
- 两个数据目录**并存、非同一事物的两个版本**：`C:\Users\Admin\.workbuddy\workbuddy.db`（国内版应用数据）与 `C:\Users\Admin\.workbuddy-ai\skills\`（技能根）均存在。
- `~\.dsh\.workbuddy-*.json` 六个已于 11-07 移走（实测 NONE），`.credentials.yaml` 保留——与本记录后节一致。
- dsh-workbuddy-connect 现为 **0.7.8**（profile `pnpm-workspace.yaml` minimumReleaseAgeExclude 所载；记录当时 0.7.2）。
- 本记录的方法论（中文注册表值触发兜底、param 不绑定、判归属看真实进程参数、走本机接口读插件状态）仍有效；具体路径/版本以现查为准。

## 关联

- 相关记录：[[踩坑-第三方Claude客户端自带服务商配置切全局路由无效]]（同为"判归属要看真实进程/参数"）、
  [[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]（同为 PS 5.1 语义坑）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 取证脚本：`G:\AIrenwu\01_任务归档\2026-10-11_逆向工具箱体检\03_工具脚本\` 下 `repro_fallback.py`、`why_exit3.py`、
  `ascii_budget_probe.py`、`repro_discovery.py`、`set_workbuddy_env.py`
