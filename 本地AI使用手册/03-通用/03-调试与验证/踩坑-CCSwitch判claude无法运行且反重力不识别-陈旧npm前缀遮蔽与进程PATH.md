---
title: "CC Switch 判 Claude Code 无法运行、三工具重复安装、Antigravity 不识别：陈旧 npm 前缀遮蔽 + 进程 PATH 陈旧"
date: 2026-11-24
domain: common
category: 03-调试与验证
status: verified
severity: medium
stack: [CC Switch 4.0.40, Claude Code 2.1.331, Codex 0.172.0, Pi 1.6.0, agy 1.5.15, npm, Windows 11]
tags: [CC Switch, npm prefix, PATH 遮蔽, junction, 自更新中断, Antigravity, agy, 环境变量冲突]
---

# 问题：CC Switch 报 claude.exe 不是内部或外部命令、claude/codex/pi 各「另有 1 处安装」、装了 Antigravity 却显示未安装

## 一句话结论

三个症状同源于「陈旧 npm 全局前缀 D:\node-global（含 junction C:\node-global）在 PATH 里遮蔽健康前缀 Roaming\npm」+「Claude Code 自更新中断只留下 claude.exe.old.*」；Antigravity 不识别则因为 CC Switch 该条目管的是 **CLI（agy）** 而非桌面 IDE，且 CC Switch 安装枚举只用**进程继承的 PATH**，老父进程拉起的 GUI 看不到新加的 PATH。

## 触发条件与影响

- 项目或功能：CC Switch「应用」页安装检测；终端里 claude/codex/pi 命令。
- 环境与版本：Windows 11；CC Switch 4.0.3x→4.0.40（2026-11-24 09:33 自更新）；npm prefix=C:\Users\Admin\AppData\Roaming\npm；用户 PATH 顺序 D:\node-global;C:\node-global;…;Roaming\npm。
- 触发条件：①Claude Code 自更新把 exe 改名 `.old.<毫秒时间戳>` 后新 exe 未落盘（本机今早 09:29 一次中断更新）；②历史遗留第二 npm 前缀未清；③只装了 Antigravity 桌面 IDE（D:\Antigravity\Antigravity.exe）没装 agy CLI；④加完 PATH 不重启 GUI。
- 影响范围：claude 命令直接报「不是内部或外部命令」；CC Switch 把陈旧安装标「无法运行/默认」；codex/pi 命中旧版 0.169.0/1.5.2；Antigravity 躺在「未安装」列表。

## 复现步骤

1. 前置条件：存在两个 npm 全局前缀且陈旧者 PATH 靠前；陈旧前缀里 claude-code 包 bin 目录只有 `.old` 文件。
2. 操作或命令：`where.exe claude`；`D:\node-global\claude.cmd --version`；CC Switch 应用页观察。
3. 预期结果：单一健康安装、版本最新、Antigravity（CLI 已装时）显示已安装。
4. 实际结果：三套 claude 入口；陈旧 cmd 报 `"D:\node-global\node_modules\@anthropic-ai\claude-code\bin\claude.exe" 不是内部或外部命令, 也不是可运行的程序或批处理文件。`；CC Switch 三条「另有 1 处安装」；Antigravity 未安装。

## 证据

- `D:\node-global\node_modules\@anthropic-ai\claude-code\bin\` 仅 `claude.exe.old.1795483754116`（372,461,728 B），无 claude.exe；`D:\node-global\claude.cmd` 末行 `"%dp0%\node_modules\@anthropic-ai\claude-code\bin\claude.exe" %*`。
- `Get-Item C:\node-global` → Junction，Target=D:\node-global（同一份陈旧前缀挂两个 PATH 入口）。
- 版本对照：Roaming\npm = claude 2.1.331 / codex 0.172.0 / pi 1.6.0；D:\node-global = codex 0.169.0 / pi 1.5.2 / claude 坏。pi 包名 `@earendil-works/pi-coding-agent`。
- 修复后截图：`G:\AIrenwu\01_任务归档\2026-11-24_CC-Switch重复安装与反重力识别\04_产物\ccswitch_final.png`（已安装·7，Claude Code/Codex/Pi 均单一路径 Roaming\npm\*.cmd，Antigravity CLI = D:\agy\bin\agy.exe，无「无法运行」、无「另有 1 处安装」、无环境变量冲突横幅）；09:55 补拍 `ccswitch_final2.png` 版本列已落定：2.1.331 / 0.172.0 / 1.6.0 / agy 1.5.15，更新弹窗亦已消失。
- 上游佐证：[issue #9810](https://github.com/farion1231/cc-switch/issues/9810)（enumerate_tool_installations 只用进程 PATH）、[v4.0.18 release](https://newreleases.io/project/github/farion1231/cc-switch/release/v4.0.18)（agy 作为独立托管应用）、[PR #9893](https://github.com/farion1231/cc-switch/pull/9893)（4.0.40 新增 agy-desktop 桌面探测）、[环境变量冲突文档](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/zh/5-faq/5.4-env-conflict.md)（ANTHROPIC 开头用户变量一律告警）。

## 根因分析

- 已确认的根因：①自更新中断留 `.old` 残骸 → cmd 指向不存在 exe；②陈旧前缀 PATH 靠前遮蔽健康前缀（junction 使「两处」实为同一份）；③CC Switch Antigravity 条目只认 agy CLI，IDE 不算（4.0.40 起 IDE 走独立 agy-desktop 条目）；④安装枚举用进程 PATH，父进程环境陈旧则新 PATH 不可见；⑤用户注册表遗留 `ANTHROPIC_TARGET_API_URL=http://127.0.0.1:15721` 触发 4.0.40 环境变量冲突横幅（~/.claude 与 cc-switch.db 均无消费方，属冗余覆盖源）。
- 排除过的假设：CC Switch 配置损坏（settings/live-state 正常）；代理端口 7897（已不监听，现用 7890）；IDE 自带 CLI（D:\Antigravity\UserData\bin\agy-node.cmd 只是 ELECTRON_RUN_AS_NODE 包装，不含 agy）。
- 问题归属：环境或依赖（历史遗留前缀 + 一次中断的自更新），非本次修改引入。

## 最小修复

1. 备份后移走陈旧前缀的 claude*/codex*/pi* 九个入口 + `node_modules\@anthropic-ai`、`@openai`、`@earendil-works` 三包到 `G:\AIrenwu\01_任务归档\2026-11-24_CC-Switch重复安装与反重力识别\04_产物\backup\node-global`（保留 motrix/nodemon/npm/npx/corepack）；单一健康安装=Roaming\npm（与 npm prefix 一致且版本最新）。该备份已于同日稍晚按用户授权删除（见剩余风险）。
2. 官方脚本装 CLI：`curl -fsSL https://antigravity.google/cli/install.cmd` → `install.cmd -d D:\agy\bin`（curl 认 HTTP(S)_PROXY 环境变量，注入 127.0.0.1:7890；install.cmd 的参数 sanitize 禁止 CMDCMDLINE 含 `&|;<>^`，故不能 `cmd /c "set …&&…install.cmd"` 包装，要在调用壳里设环境变量）。agy.exe 239,256,728 B，v1.5.15，自动写用户 PATH。
3. 备份后删除用户变量 `ANTHROPIC_TARGET_API_URL`（备份 JSON 同归档 backup 目录），消横幅并消除「脱离 CC Switch 后仍被钉死到代理端口」的隐患。
4. 用**注册表实时 PATH**（Machine+User 拼接）重启 CC Switch，使其进程环境看见 D:\agy\bin；taskkill 后立刻 Start-Process，attach 会自动重写客户端配置回路由模式。

## 验证记录

- [x] 格式化或静态检查：不适用（环境修复）。
- [x] 类型检查或编译：不适用。
- [x] 单元、集成或端到端测试：`where.exe claude/codex/pi` 各仅 Roaming\npm 两条（无扩展名+.cmd）；`claude --version`=2.1.331、`codex --version`=0.172.0、`pi --version`=1.6.0、`D:\agy\bin\agy.exe --version`=1.5.15。
- [x] 构建：不适用。
- [x] 启动或手动回归：CC Switch 4.0.40 重启后应用页截图 ccswitch_final.png：已安装·7 含 Antigravity CLI（D:\agy\bin\agy.exe），三工具单一路径、无报错行、无冲突横幅；日志确认代理 127.0.0.1:15721 启动且 claude/codex attach 回路由。
- [x] 清理后复查（2026-11-24 09:59）：注册表实时 PATH 下 where.exe claude/codex/pi/agy 均单一入口（agy=D:\agy\bin\agy.exe）；版本 2.1.331 / 0.172.0 / 1.6.0 / 1.5.15；两前缀 *.old.* 递归扫描为空；ANTHROPIC_TARGET_API_URL 用户变量已空；CC Switch pid 40992 日志代理 127.0.0.1:15721 启动、claude/codex attach 路由正常；复查截图 ccswitch_recheck.png 与 ccswitch_final2.png 逐字节一致（界面零回归）。
- 取证手法：用户活跃时不抢前台——`ShowWindow(hwnd, SW_SHOWNOACTIVATE=4)` 显示隐藏主窗口 + `pwcap.py` PrintWindow 后台抓图（脚本同归档 03_工具脚本\show_noactivate.py）。

## 可复用规则

- CLI 报「不是内部或外部命令」且 cmd 包装存在时：先 Test-Path 包装指向的真实 exe，再看同目录有无 `.old.*` 残骸（自更新中断特征），别先怀疑 PATH 全表。
- 判「重复安装」：`where.exe` 全清单 + junction 归一（Get-Item 看 LinkType/Target）+ 逐份版本比对；保留与 `npm config get prefix` 一致且最新的那份，其余备份后移走入口与包目录。
- 给系统加 PATH 后，已运行 GUI（尤其安装检测类）必须用注册表实时 PATH 重启才可见；从老父进程（服务/常驻壳）Start-Process 会继承陈旧环境。
- CC Switch 的 Antigravity 条目=agy CLI；桌面 IDE 在 4.0.40 走 agy-desktop 独立条目；「装了 IDE 却显示未安装」不是 bug。
- 删用户环境变量前：grep 消费方（客户端配置目录 + 应用 db）确认冗余，备份 JSON 再删；CC Switch 对 ANTHROPIC/OPENAI/GEMINI/XAI 前缀用户变量一律告警。
- 本机执行壳注意：工具名 pwsh 实为 PowerShell 5.1，**内层再调 `pwsh` 会 CommandNotFound**；代理端口以实测监听为准（本次 7890，记忆里的 7897 已死）。

## 适用范围与不适用范围

- 适用：Windows 多 npm 前缀遗留、CC Switch 安装检测类误报、agy CLI 官方安装、PATH 变更后 GUI 不刷新。
- 不适用：macOS launchd 窄 PATH 同类问题（机制同但修法不同，见 issue #9810）；npm 包自身损坏（需重装而非移入口）。

## 剩余风险

- 陈旧前缀备份（1,375,634,939 B）已按用户 2026-11-24「将垃圾清理」授权删除，G 盘释放约 1.30 GB；回滚途径改为 npm 重装旧版（codex@0.169.0、pi@1.5.2，入口 cmd 由 npm 重建），不再依赖本地备份。D:\node-global 与 junction C:\node-global 仍留在 PATH（目录里还有 @motrix/nodemon 等，未动）。
- agy CLI 尚未登录（凭据目录 ~/.gemini/antigravity-cli 未生成）；登录含账号手机验证，只能用户本人完成。
- CC Switch 4.0.40 更新说明弹窗在 09:55 截图已消失（已被关掉）；若再弹出点一次「知道了」即可，不影响检测。

## 关联

- 相关记录：[[踩坑-TraeCN自更新改名留旧快捷方式致开始菜单两个Trae实为同一程序]]（自更新残骸同类）、[[规则-CCSwitch接OpenAI兼容网关要四件套配置]]、[[踩坑-杀软断网修复清零系统代理且StateListen过滤假报端口死]]（代理端口实测）。
- 相关分类：03-通用/03-调试与验证。
- 相关代码、命令或文档：归档 `G:\AIrenwu\01_任务归档\2026-11-24_CC-Switch重复安装与反重力识别\`（03_工具脚本：move_old_globals.py、show_noactivate.py、db_probe.py、install.cmd、run_install.ps1；04_产物：env 备份 JSON 与前后截图，node-global 备份已按用户授权清理）。