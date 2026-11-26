---
title: 反重力汉化每次需单跑工具：动态 CDP 注入随会话消失，用官方一键快捷方式并 repoint 原启动入口整合
date: 2026-11-24
domain: common
category: 03-调试与验证
status: verified
severity: medium
stack: Windows 11 / Electron / Go 单文件工具 / CDP / WScript.Shell lnk
tags: [Antigravity, 反重力, 汉化, antigravity-hans, CDP, 快捷方式, 启动整合, 自动更新]
---

# 一句话结论

普通版 Antigravity 的汉化工具 antigravity-hans 走**动态 CDP 注入**（注入随页面关闭消失），所以每次启动应用都要单跑工具；静态补丁 `--patch` **仅支持 Antigravity IDE** 且不含 Swarm 会话页，对普通版不可用。整合正解＝官方 `--shortcut --app` 生成的一键启动链（`conhost.exe --headless "<hans.exe>" --app --nogui`），并把用户**原有开始菜单 lnk 备份后 repoint** 到同一条命令，名字图标不变、习惯不变。其上再包一层 launch.ps1 自动更新包装器（用户 2026-11-24 追加诉求）：每次启动比对 GitHub releases/latest 资产 digest，有新版则校验+备份旧 exe+替换后再启动，任何检查失败回落旧版不阻塞启动。

# 触发条件与影响

- 用户装了 github.com/yuexps/Antigravity-Hans 的 Windows 单文件 exe，每次启动 Antigravity 后还要双击汉化工具才变中文。
- 影响：体验割裂；误以为工具"没装好/没生效"。
- 追加诉求：汉化工具上游更新后旧词库配新应用会出问题，要求每次启动自动检查并更新工具。

# 复现步骤

1. 双击 D:\Antigravity\Antigravity.exe（或原开始菜单快捷方式）→ 英文界面。
2. 再跑 antigravity-hans-windows-amd64.exe 选 APP → 变中文；关掉应用重开又英文。

# 证据

- 产品身份：D:\Antigravity\Antigravity.exe VersionInfo ProductName=Antigravity、ProductVersion=2.35.0.0；卸载注册表 DisplayName="Antigravity 2.35.0"；%LOCALAPPDATA%\Programs\Antigravity IDE 不存在 → **普通版，非 IDE**。
- 工具机制（README + exe 字符串）：动态=CDP `Page.addScriptToEvaluateOnNewDocument`/`Runtime.evaluate`/`webSocketDebuggerUrl`，不改安装目录；静态标记 workbench.html/product.json/argv.json/`window.__antigravityZhPatchFingerprint` 仅 IDE 路径。
- 官方快捷方式实测目标：`C:\Windows\System32\conhost.exe` + `--headless "D:\AI-Tool-State\antigravity-hans\antigravity-hans.exe" --app --nogui`（conhost --headless 隐藏监视器控制台；--nogui 无交互）。
- 启动链实测：应用命令行带 `--remote-debugging-port=58321 --remote-debugging-address=127.0.0.1`（端口由启动链开，外部守护 attach 不到普通启动的实例）；监视器 pid 文件 C:\Users\Admin\AppData\Roaming\antigravity-hans\monitor-antigravity.pid。
- 抓图证实中文：菜单「工作区/查看/窗口」、侧栏「新建对话/自动化/自定义/项目」、主区「嗨，Grii，今天想构建什么?」、输入框「询问什么都可以。@ 引用，/ 执行动作」、右下 EN 切换圆钮。见归档 04_产物\hans_launch_capture.png 与 verify_result.json。
- exe SHA256=A1330F1F955515D5024F403C343384F04FEE2D1A4E8FDB58D1C0BEE978C259FA（H:\下载 原件与稳定副本一致）。
- 上游发布事实：GitHub repos/yuexps/Antigravity-Hans releases/latest = v0.5.0（2026-11-23）；windows 资产 digest sha256:a1330f1f955515d5024f403c343384f04fee2d1a4e8fdb58d1c0bee978c259fa == 本机 exe 哈希；API 资产自带 digest 字段→校验无需每次下 SHA256SUMS（无 digest 才回落解析）；直连与代理 127.0.0.1:7890 均 http=200 约 1.0s。

# 根因分析

动态注入是**会话级**的：CDP 脚本注入活在当前页面/进程里，应用退出即消失；监视器进程也必须随应用启动并拿到调试端口。因此"装一次永久汉化"在普通版上不存在（静态补丁只覆盖 IDE 且不含会话页）。用户每次单跑工具不是故障，是模式使然；要"启动即汉化"只能把监视器纳入启动链。

# 最小修复

1. 稳定目录 D:\AI-Tool-State\antigravity-hans\antigravity-hans.exe（从 H:\下载 复制，哈希核对；下载目录易被清理、ASCII 路径避编码坑）。
2. `antigravity-hans.exe --shortcut --app` → 桌面生成「Antigravity 中文.lnk」。
3. 备份开始菜单 C:\Users\Admin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Antigravity.lnk 后 repoint：Target=conhost.exe；Arguments=--headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\AI-Tool-State\antigravity-hans\launch.ps1"；WorkingDirectory=稳定目录；IconLocation=D:\Antigravity\Antigravity.exe,0（名字图标不变）。桌面「Antigravity 中文.lnk」同改此链；改前备份 *.chain1.bak。
4. launch.ps1＝自动更新包装器（纯 ASCII）：每次启动 Get-FileHash 本地 exe → curl releases/latest（-m 10，失败回落注册表 ProxyServer 代理）→ 比对 windows 资产 digest（无 digest 回落解析 SHA256SUMS）→ 不同则 curl -L -m 90 下载 update.download.exe → 哈希校验 → Copy 旧 exe 到 backup\antigravity-hans.prev.exe → Move 替换（被监视器锁定则先 `exe --stop < NUL` 重试一次）→ 写 version.json → 再 Start-Process "<稳定目录 exe>" '--app','--nogui' -WindowStyle Hidden；任何失败只记 update.log（超 200KB 截尾 100 行）并回落旧版启动，不阻塞。-CheckOnly 只检查不启动。
5. 不做 IFEO/进程钩子/开机守护：普通启动不开调试端口，守护只能 attach 失败或重启应用，体验更差。

# 验证记录

- 空闲门控脚本（用户空闲≥10s 才动 GUI）用与 lnk 完全相同命令行启动：app_pid=31720、窗口标题 Antigravity、监视器进程在、命令行含调试端口；PrintWindow 抓图全中文（见证据）。
- 验证后 `hans --stop` + taskkill 恢复原状，remaining_pids=[]。
- 自动更新分支隔离实测（D:\AI-Tool-State\hans-update-test 假旧 exe）：下载→校验→备份→替换全链 5s，替换后哈希与上游 digest 吻合，测毕目录已删。
- 编码坑修复复验：conhost --headless 下 -CheckOnly 记 `up-to-date tag=v0.5.0 sha256=a1330f1f…`（2026-11-24 10:59:13）；修复前同环境 ConvertFrom-Json 报 error(12410) 但回落机制仍保证启动+中文（capture2 全中文）。
- 全链复验（verify_hans_launch2.py，11:08:15 空闲门控）：链内 update.log `up-to-date tag=v0.5.0`+`launched monitor chain`，app_pid=21956 带调试端口，抓图全中文，11:08:37 清理 remaining_pids=[]；产物归档 04_产物\verify_result2.json、hans_launch_capture2.png。
- 回滚备份：归档 04_产物\backup\Antigravity.startmenu.lnk.bak（767 B）、*.chain1.bak（改链前 lnk）、D:\AI-Tool-State\antigravity-hans\backup\antigravity-hans.prev.exe（更新前 exe）。

# 可复用规则

- 判"汉化工具为何每次要跑"先看模式：CDP 动态=会话级必须随启动；静态补丁看产品分支（IDE vs 普通版）与覆盖范围（内嵌智能体/Swarm 页常不含）。
- 整合第三方启动器优先复用其官方 shortcut/wrapper 产物，再 repoint 用户**现有**入口（备份 lnk 原件），而不是教用户改习惯或自写守护。
- 读 lnk 用 WScript.Shell COM；PS 5.1 里 `foreach(...){...} | pipe` 非法，要 `$(foreach...)` 包起来。
- 取 Go 交互菜单 exe 的 usage：写 ASCII .cmd 用 `< NUL` 重定向再跑；Start-Process -RedirectStandardInput 'NUL' 会被解析成工作目录下的 NUL 文件报 FileNotFoundException。
- 含中文路径的 exe 先复制去 ASCII 稳定目录再进启动链，哈希核对保持一致。
- conhost --headless 下控制台码页是 OEM936：PS 5.1 按它解 curl stdout 的 UTF-8 中文会出杂散反斜杠致 ConvertFrom-Json 失败（交互会话里同代码却正常）；改 `curl -o 临时文件` + `Get-Content -Raw -Encoding UTF8`，不依赖控制台解码。
- 自动更新包装器必须"检查失败不阻塞启动"：记日志+回落旧版；替换前留 prev.exe 可回滚；exe 被监视器锁定时先 --stop 再重试替换。

# 适用范围与不适用范围

- 适用：普通版 Antigravity + yuexps/Antigravity-Hans（README 适配 2.34.0，本机 2.35.0 实测可用）；Windows 10 1809+（conhost --headless）。
- 不适用：Antigravity IDE 想要"零进程永久汉化"→ 走 `--patch` 静态（但会话页仍需动态）；直接双击安装目录 exe 的启动方式不被本整合覆盖（仍英文）。

# 剩余风险

- 应用大版本更新后词库滞后：先 `--stop` 再按新图标启动；杀软对未签名 Go exe 启发式误报按 Release SHA256SUMS 核对。
- 监视器残留：--nogui 会清理同会话无窗口残留；仍有可见窗口时会中止重启，需手动退出。
- 开始菜单 repoint 后若用户用第三方启动器/直接双击 exe，仍英文；属原理边界非故障。
- 自动更新依赖 GitHub API 可达（直连或代理回落）；长期不可达时保持旧版（update.log 可见），不影响中文启动。
- 上游新版若与当前应用版本不兼容：首次启动会自动换新版，需手动 --stop 并用 backup\antigravity-hans.prev.exe 回滚。

# 关联

- 归档：G:\AIrenwu\01_任务归档\2026-11-24_反重力汉化与启动整合\（01_报告\整合说明.md、03_工具脚本\verify_hans_launch.py、verify_hans_launch2.py、04_产物\hans_launch_capture.png、verify_result.json、hans_launch_capture2.png、verify_result2.json、修复前首验同名产物 *.prefix、backup\Antigravity.startmenu.lnk.bak、*.chain1.bak）
- 自动更新链实体：D:\AI-Tool-State\antigravity-hans\launch.ps1、update.log、version.json、backup\antigravity-hans.prev.exe
- 上游：https://github.com/yuexps/Antigravity-Hans（releases/latest API 资产带 digest 字段，校验无需每次下 SHA256SUMS）
- 同日前序：[[踩坑-CCSwitch判claude无法运行且反重力不识别-陈旧npm前缀遮蔽与进程PATH]]（CC Switch 的 Antigravity 条目=agy CLI，与桌面版本整合无关）