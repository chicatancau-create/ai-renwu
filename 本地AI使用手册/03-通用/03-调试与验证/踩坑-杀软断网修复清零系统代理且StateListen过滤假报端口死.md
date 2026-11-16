---
title: "杀软「断网修复」把系统代理开关清零；Get-NetTCPConnection 加 -State Listen 会假报端口没人监听"
date: 2026-11-06
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: high
stack: [Windows 11, WinINET, Clash Verge Rev, PowerShell, 火绒安全]
tags: [系统代理, ProxyEnable, 端口监听, 断网修复, WLAN, 唤醒, NDIS, 取证顺序]
---

# 踩坑：杀软"断网修复"清零系统代理 + `-State Listen` 假报端口死，两个叠一起把排查带偏

> 复盘日期 2026-11-06。上一轮（同日 16:0x）我据 `-State Listen` 的空结果断言"内核活着却一个端口都没监听"，
> 那一轮结论**是假的**，本条记录的首要价值是把这个假阴性钉死。

## 一句话结论

「网络老出问题」在这次其实是**两件事**：① 火绒「断网修复」把 `ProxyEnable` 从 1 清成 0（`ProxyServer` 原样保留），
于是**直连全通、走系统代理的全挂**，杀软自己却显示"正在修复"；② 我用的判活命令
`Get-NetTCPConnection -LocalPort 7897 -State Listen` 在本机（Win11 build 28000）**返回空**，
而不加 `-State` 过滤时同一个端口明明在 —— 这个假阴性让我误判"代理内核没监听"，差点去重启 Clash。
规则：**判端口死活不要带 `-State Listen`**；**"直连通、代理挂"这个组合唯一指向 `ProxyEnable`/代理链路，不要往内核或 DNS 上想**。

## 触发条件与影响

- 项目或功能：本机所有走 WinINET 的程序（浏览器、Office、多数桌面客户端）访问 GitHub / Google 等需要代理的站点。
- 环境与版本：Windows 11（10.0.28000）+ Clash Verge Rev 2.5.10 服务模式（内核 `verge-mihomo` 由 `clash-verge-service` 托管）；
  `ProxyServer=127.0.0.1:7897`，`ProxyOverride` 为默认内网段列表；WLAN 为 MediaTek Wi-Fi 6E MT7922。
- 触发条件：运行火绒安全 → 断网修复（它的动作会清 `ProxyEnable`、并重启 WLAN 扩展模块/网卡）。
- 影响范围：代理链路整体失效，但 `nslookup`、直连站点、`git`（按 URL 单独配了 `http.<url>.proxy`）**全部正常**，
  极易被误判成 DNS 污染、代理内核死亡或驱动故障。

## 复现步骤

1. 前置条件：Clash Verge 开「系统代理」，`ProxyEnable=1`，`curl -x http://127.0.0.1:7897 https://github.com` 回 200。
2. 操作：在火绒里点「断网修复」。
3. 预期结果：——（这是要避免的错误做法）
4. 实际结果：`ProxyEnable` 变 0、`ProxyServer` 未变；7897 **仍在监听**；
   `https://www.baidu.com` 直连 200，而浏览器里 GitHub 打不开。
   此时执行 `Get-NetTCPConnection -LocalPort 7897 -State Listen` 得 0 条，
   执行 `Get-NetTCPConnection -OwningProcess <内核PID>` 却看到 `:: 7897`（State 列为空）。

## 证据

- `02_证据日志\恢复系统代理开关.txt`：16:25:27 `ProxyEnable = 0` → 16:25:31 `= 1`；
  随后 `via7897 github -> 200`、`google/generate_204 -> 204`、`youtube -> 200`、`direct baidu -> 200`。
- `02_证据日志\网络稳定性体检-只读.txt` / `网络稳定性体检2-只读.txt`：
  - 假阴性对照：`-LocalPort 7897 -State Listen` 计数 0；`-OwningProcess 32896` 列出 `:: 7897`；`-LocalPort 7897`（无 State）列出 OwningProcess 32896、State 空白。
  - 服务模式其实完好：内核 PID 32896 的父进程 = 6840 = `clash-verge-service.exe`，服务 `Running/Automatic`（所以本轮**没跑** `verge_recover.ps1`）。
  - `nslookup -timeout=3 www.baidu.com` 分别指向 `192.168.55.131`/`223.5.5.5`/`119.29.29.29` **都能出答案** ⇒ DNS 无故障。
- 「时好时坏」的分层归因（7 天窗口）：
  - 唤醒 18 次（`Power-Troubleshooter` Id=1）；WLAN `8001 已成功连接` 与唤醒时刻逐个对齐（差 1–70 秒），
    其间夹 `8002 无法连接` + `8011 连接到上一个正常网络` —— 这是**唤醒后重连的正常形态**，不是故障。
  - 但 15:56:59 / 15:58:31 / 16:05:50 三次重连**没有对应的唤醒**，其前 1 分钟内各有
    System `Id=10002 WLAN 扩展模块已停止`（15:56:06 / 15:57:48 / 16:05:06）—— 时间点正是火绒断网修复的操作窗口。
  - 另一条独立线索：NDIS `Id=10400` 于 14:11–14:52 对 `"Remote NDIS based Internet Sharing Device #3"`
    报"硬件停止响应命令"并重置 **10 次**，实例 `USB\VID_2717&PID_FF88`（小米手机 USB 共享上网）；
    10-31 还有一条 `Id=10317 Fatal error: miniport has failed a power transition`。它不参与当前默认路由（默认路由只有 WLAN metric 35 与 Radmin VPN metric 9257），但会制造"网络抖动"的观感。
- `02_证据日志\网络一键修复.txt`：修复脚本幂等自检（已 1 则不改，报"本来就是 1，未改动"）。

## 根因分析

- 已确认的根因：
  1. `ProxyEnable` 被第三方"断网修复"清零 ⇒ 走 WinINET 的程序改走直连 ⇒ 需代理的站点全灭。
  2. `Get-NetTCPConnection` 在本机对双栈监听项（`LocalAddress=::`）的 `State` 返回**空值**，
     因此 `-State Listen` 精确匹配不到 ⇒ 端口死活判据被命令自己骗了。
- 排除过的假设（都曾是错的）：
  - ~~代理内核没监听 7897~~（上一条假阴性所致，实测一直监听且代理直连都通）。
  - ~~DNS 挂了~~：`Resolve-DnsName -Server X -DnsOnly -Timeout 3` 报 `NamedParameterNotFound`，
    3 毫秒内失败，看起来和"解析超时"一模一样 —— **这个坑本手册已有记录，本次又踩了第二次**；
    换成 `nslookup -timeout=3` 立刻证明三台 DNS 都正常。
  - ~~Clash 服务模式又退回 Sidecar~~：父进程判据通过，无需修复。
  - ~~WLAN 驱动频繁掉线~~：与唤醒对齐的重连属正常；异常的那三次由杀软重启扩展模块引起。
- 问题归属：**环境或第三方软件**（杀软）+ **我自己的取证命令用错**。

## 最小修复

1. `HKCU\...\Internet Settings\ProxyEnable = 1`，并广播 `WM_SETTINGCHANGE`（否则已开着的程序不会重读）。
2. 交付**无需管理员权限**的一键自检修复件（纯新增，未动任何配置）：
   - `G:\AIrenwu\01_任务归档\2026-11-03_后台进程盘点\03_工具脚本\网络一键修复.ps1` + 同名 `.bat`（GBK+CRLF）
   - 桌面快捷方式 `网络一键修复.lnk`
   逻辑：查 `ProxyEnable` → 查 7897（**不带 `-State`**）→ 端口死才拉起服务与 GUI 并轮询 → 只在需要时改注册表并广播 → `curl` 双路（走代理 github / 直连 baidu）自证。
   实测（健康态）：全路径 4 秒，幂等，输出"网络已恢复"。

## 验证记录

- [x] 修复前基线：`ProxyEnable=0`、7897 有监听、直连 200、`git ls-remote` 因走 7897 而可用（代理进程活着，只是系统代理关了）
- [x] 改后注册表回读：`ProxyEnable=1`
- [x] 端到端：`github 200` / `generate_204` / `youtube 200` / 直连 `baidu 200`
- [x] 真实消费者：`git ls-remote --heads origin`（E:\fullstack-code，经 `http.https://github.com.proxy`）rc=0
- [x] 一键修复件在健康态复跑：无副作用、结论正确、日志可读（UTF-8）
- [ ] 未验证：不点杀软断网修复就无法制造同样故障复现；本轮只做了"症状—根因—修复"闭环，未重复触发杀软

## 可复用规则

1. **判 TCP 端口死活**：`Get-NetTCPConnection -LocalPort N`（不加 `-State`），看有没有条目 + `OwningProcess`；
   本机对 `::` 双栈监听 `State` 会是空值，`-State Listen` 恒得 0 条。要更稳就直接 `curl -x http://127.0.0.1:N <需要代理的站点>`。
2. **"直连通、走代理不通"只查三样**：`ProxyEnable` → `ProxyServer` 是否还在 → 代理端口是否有人监听。
   不要动 DNS、不要重启内核、不要怀疑驱动。
3. **网络"老出问题"先做时间对齐**：把 `WLAN-AutoConfig/Operational` 的 8001/8002/8011 与
   `Power-Troubleshooter` Id=1（唤醒）比对时刻；**贴着唤醒的是正常重连**，不贴唤醒而贴着
   `System 10002（WLAN 扩展模块已停止）`/`NDIS 10400/10317` 的才是要查的异常，再看它贴着哪个第三方软件的操作时间。
4. **动过第三方"修复"类工具之后**，必须回读它可能改的项：`ProxyEnable`、各网卡 DNS、`netsh winsock reset` 痕迹；
   它报错面板上的"修复中/已修复"不能当"没改坏"的证据。
5. `Resolve-DnsName` 不要带 `-Timeout`（本 build 无此参数，会在 3ms 内抛 `NamedParameterNotFound`）；
   要限时用 `nslookup -timeout=N -retry=1 <host> <server>`。

## 适用范围与不适用范围

- 适用：Windows 11 上用 WinINET 系统代理 + 本地代理软件（Clash/v2ray 类）的桌面机；判"到底哪一层断了"的分层取证。
- 不适用：程序自己配了代理（如 git `http.<url>.proxy`、环境变量 `HTTPS_PROXY`）时，`ProxyEnable` 与它无关；
  纯直连环境、代理浏览器插件（SwitchyOmega 类）不适用第 2 条。

## 本机痕迹（非通用经验，仅作记录）

- 待你决定的两项预防（都改网卡配置，我没动）：
  MT7922 高级属性 `LowPowerEnable=Auto`、`RoamIndicateTh=5.中高` 可改成节能关闭 / 漫游门槛最低，
  代价是**笔记本耗电增加**；小米手机 USB 共享上网（`VID_2717&PID_FF88`）的 RNDIS 适配器今日本已重置 10 次。
- 脚本与日志：`G:\AIrenwu\01_任务归档\2026-11-03_后台进程盘点\03_工具脚本\{网络一键修复.ps1,.bat,net_stability_readonly.ps1,net_stability_readonly2.ps1,restore_system_proxy.ps1}`、
  `02_证据日志\{恢复系统代理开关.txt,网络稳定性体检-只读.txt,网络稳定性体检2-只读.txt,网络一键修复.txt}`。
- `03_工具脚本\verge_recover.ps1` 本轮**未执行**（服务模式判据通过，不需要）。

## 补充：2026-11-13 再确认（FlClash 7890 同款；客户端 State 过滤一样漏）

- 清理 clash 残留目录前后判代理健康：`Get-NetTCPConnection -LocalPort 7890 -State Listen` 得 0 条；去掉 `-State` 参数但客户端仍 `Where-Object State -eq 'Listen'` **还是 0 条**——一度误写成「表本身漏监听者」（未正确验证就下结论，违反判据纪律，已当场纠正）。
- 完全不带 State 筛选的原始查询证实机制与本记录根因 2 一致：监听条目**在表里**（`LocalAddress=:: LocalPort=7890 OwningProcess=39896`=FlClashCore），**State 列为空**。新增细化：**任何按 State 的过滤都等价地坏**——cmdlet `-State Listen` 参数与客户端 `Where-Object State -eq 'Listen'` 一样漏；「不加 -State」必须理解为**完全不按 State 筛**，只看条目存在性 + OwningProcess。
- 金标准复验：`Test-NetConnection 127.0.0.1 -Port 7890` → TcpTestSucceeded=True（真实握手）；删除目录后 `git ls-remote`（GitCode 真实 remote、直连）rc=0。端口一直活着，判据命令自己骗人的模式在 FlClash/7890 上再次应验。
- 工程落地：`clash-cleanup-worker.ps1` / `clash-cleanup-precheck.ps1` 的端口健康检查已改用真实 TCP 测试（Test-NetConnection），不依赖 State；脚本已入 ai-renwu 仓库。
