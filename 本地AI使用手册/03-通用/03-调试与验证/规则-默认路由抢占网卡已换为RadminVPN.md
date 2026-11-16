---
title: "接力：抢走默认路由的低 metric 虚拟网卡换成了 Radmin VPN（2026-10-13 实测）"
date: 2026-10-13
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: high
stack: [Windows, Radmin VPN, PowerShell, NetAdapter]
tags: [网络取证, 路由, 假超时, 接力]
---

# 问题：默认路由又被一块虚拟网卡抢了，这次是 `Radmin VPN`（metric=1），不是 Meta Tunnel

## 一句话结论

这条是 [[踩坑-虚拟网卡空metric抢走默认路由致域名假超时]] 的**接力记录**：
那条记的 `Meta Tunnel` + RNDIS 组合在本机已不成立，**但「低 metric 虚拟网卡抢走默认路由」这个模式完全没变**。
2026-10-13 实测，抢路由的是 **`Radmin VPN`：`InterfaceMetric=1`、`AutomaticMetric=Disabled`、`Connected`**。
**结论不要写死网卡名，每次都要现查。**

## 触发条件与影响

- 环境与版本：Win11 28000；`以太网 2`（`192.168.0.1`）为真实 uplink，`WLAN` 已断开。
- 触发条件：装了带虚拟网卡的桌面软件（Radmin VPN / Meta 系 / 各类加速器）并置 `AutomaticMetric=Disabled`。
- 影响范围：与上一条相同——不走系统代理的程序（Node/Electron/Rust 自带 HTTP 栈）可能被灌进隧道，
  表现为某些域名直连一律超时、走代理却正常；代价是排查方向容易被带偏到 DNS 或目标站。

## 复现步骤（本次为状态取证，非故障复现）

1. 前置条件：本机装有 Radmin VPN 且处于 Connected。
2. 操作或命令：
   ```powershell
   Get-NetRoute -DestinationPrefix '0.0.0.0/0'
   Get-NetIPInterface -AddressFamily IPv4 | Sort-Object InterfaceMetric
   ```
3. 预期结果：默认路由由真实 uplink（`以太网 2`）承担。
4. 实际结果：默认路由表里 `Radmin VPN` 以 `InterfaceMetric=1` 出现，压过 `以太网 2` 的 35。

## 证据

2026-10-13 本机实测输出：

| 出口网卡 | NextHop | RouteMetric | InterfaceMetric |
|---|---|---|---|
| **Radmin VPN** | `26.0.0.1` | 9256 | **1** |
| 以太网 2 | `192.168.0.1` | 0 | 35 |
| WLAN | `192.168.171.231` | 0 | 35 |

各网卡 metric 排序（节选）：

| InterfaceIndex | 网卡 | InterfaceMetric | AutomaticMetric | 状态 |
|---|---|---|---|---|
| **8** | **Radmin VPN** | **1** | **Disabled** | **Connected** |
| 19 | WLAN | 35 | Enabled | Disconnected |
| 24 / 22 | VMware VMnet1 / VMnet8 | 35 | Enabled | Connected |
| 18 | 以太网 2 | 35 | Enabled | Connected |
| 4 | 蓝牙网络连接 | 65 | Enabled | Disconnected |

- `Radmin VPN` 的 `AutomaticMetric: Disabled` 且手写 `InterfaceMetric=1`，**比上一条记录的"空值"更极端**：
  空值至少还可能被系统重算，写死 1 则稳定抢占。
- 对照：上一条记录里是 `Meta Tunnel` + `RNDIS`；**本次全程没有 Meta Tunnel，也没有 RNDIS**
  → 证明"换的是网卡，不换的是模式"。

## 根因分析

- **已确认的根因**：与上一条同源——默认路由优先级由 `InterfaceMetric + RouteMetric` 决定，
  第三方软件建卡时把 `InterfaceMetric` 写成极小值（或留空），压过真实 uplink。
- **排除过的假设**：
  - 不是 DNS 问题（本次未涉及解析层，直接看的是路由表出口）；
  - 不是"Radmin 装坏了"（网卡状态本身 `Connected`，属正常安装行为）；
  - 不是 `RouteMetric` 的作用（Radmin 的 `RouteMetric=9256` 明显更大，
    说明**决定胜负的是 InterfaceMetric，不是 RouteMetric**）。
- **问题归属**：环境或依赖（第三方软件建卡）。

## 最小修复

**本次未执行修改**——用户当前没有报告网络故障，且 Radmin VPN 可能是用户有意使用的工具。
**不擅自调 metric、不禁用网卡。**

若确实出现"某域名直连超时、走代理正常"，按上一条记录的修法处理：

```powershell
# 需要管理员；只降优先级，不删网卡不删路由
Set-NetIPInterface -InterfaceIndex 8 -InterfaceMetric 5000
# 回滚：Set-NetIPInterface -InterfaceIndex 8 -InterfaceMetric 1
```

## 验证记录

- [x] 默认路由出口取证：`Get-NetRoute` 三条记录，Radmin VPN metric=1 居首。
- [x] 网卡 metric 取证：`Get-NetIPInterface` 全表核对，Radmin VPN 为最低且 `AutomaticMetric=Disabled`。
- [x] 与旧记录的差异核对：本次无 `Meta Tunnel`、无 RNDIS，确认为新一轮而非旧状态残留。
- [ ] 实际影响验证：**未做**（未复现"直连超时"症状，未做带/不带代理的对照请求）。
- [ ] 修改后回归：**未做**（未执行 metric 调整）。
- [ ] 重启后是否保持：未测。

## 可复用规则

**这条记录的价值不在结论，在于"结论会过期"：**
排查"连不上某域名"时，**永远现查 `Get-NetRoute` + `Get-NetIPInterface`，不要凭记忆认定是哪块网卡**。
判据表、修复方式、`Get-NetTCPConnection` 看本地地址的取证纪律，全部沿用上一条记录。

新增一条判据：**`InterfaceMetric` 与 `RouteMetric` 同时要看，且前者通常是决定性的**
——本次 Radmin 的 `RouteMetric` 高达 9256 仍抢到了默认路由，只看 RouteMetric 会得出错误结论。

## 适用范围与不适用范围

- **适用**：Windows 上装了 TUN/VPN/加速器/远控类虚拟网卡的机器，判断默认出口归属时。
- **不适用**：代理端出口质量差导致的超时（那要换节点）；本记录**未观测到故障**，
  仅记录"路由归属已变更"这一事实，不能据此断定当前网络有问题。

## 剩余风险

**本记录只证明"路由出口是 Radmin VPN"，未证明这造成了任何实际故障**——
本次没有出现超时症状，也没有做对照实验。若后续真出现直连超时，再回到本记录并补做
"改 metric 前/后同命令对照"以升级结论。

另外：Radmin VPN 是用户可能主动使用的工具，**降它的优先级会影响它的正常功能**，
修改前应先确认用户是否在用。

## 2026-10-15 再接力：**只看 `0.0.0.0/0` 会漏掉 Cloudflare WARP 的分片接管**

本轮取证时 `Get-NetRoute -DestinationPrefix '0.0.0.0/0'` 只列出 `WLAN` / `以太网 2` / `Radmin VPN`，
**看不到 `CloudflareWARP`** —— 但 `warp-cli settings` 明明白白是 `Mode: Warp` + `WARP tunnel protocol: MASQUE`，
路由表里它装了 `0.0.0.0/5`、`128.0.0.0/3`、`112.0.0.0/4`、`100.0.0.0/10` …**一整批分片前缀**（下一跳 `192.0.2.1`、`RouteMetric=256`），
把"除例外之外的全网"接管了；同时 `Get-DnsClientServerAddress` 显示各网卡 DNS 已被改成 **`127.0.2.2 / 127.0.2.3`**（WARP 本地解析器）。

⇒ **判据升级（覆盖本条与上一条的查法）**：判"谁在接管流量"不能只查 `0.0.0.0/0`，要两条一起看：

```powershell
Get-NetRoute -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*WARP*' } | Select DestinationPrefix, NextHop, RouteMetric
Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object { $_.ServerAddresses }
```

DNS 被改成 `127.0.2.x` 是 WARP 在场的最快信号；分片前缀是它接管的实证。

同轮实测到的叠加状态：Clash 仍在听 `127.0.0.1:7897`，`HKCU\...\Internet Settings` 的 `ProxyEnable=1`，
走 7897 取出口是 `42.98.29.23 / Hong Kong / AS4760 HKT`（**不是** Cloudflare AS13335）→ 说明"应用 → Clash → Clash 自己的出站再被 WARP 抓走"是两层串联，判断出口归属时**必须分别量"走代理"和"直连"两条路**，
只看一条会得出错误结论。另记一次冷解析样本：`ipinfo.io` 首次解析 12.05 s、`Resolve-DnsName -Server 127.0.2.2` 失败一次，
随后三次 0.0 s（缓存命中）——**样本仅一次，不足以判 WARP 解析不稳定**，只能说明冷解析会慢，别据此下结论。

## 本机选型结论（2026-10-15，写给下一次会话，别重新论证一遍）

**WARP 不参与日常出境，Clash(7897) 是唯一出境口。** 依据：WARP 免费版出口是 Cloudflare 随机节点、
不能选地区，实测「直连」出口 `104.28.208.134 / AS13335 Cloudflare`，连国内基准站都被带着绕境外；
而 Clash 有规则分流和可选节点，GitHub 推送实测靠 `http.https://github.com.proxy=7897` 成功。
两者同时全接管＝套娃。WARP 留作备胎时用「本地代理」档（不接管系统），不要和 Clash 同时开「流量和 DNS」。

## 「感觉被限速」的量化判据（2026-10-15 同一轮补测）

用户报"像被限速"。分开测之后结论是**不是限速，是国内流量被自己拐上了 Cloudflare 隧道**：

| 测什么 | 实测 | 判读 |
|---|---|---|
| `1.1.1.1` ICMP 15 包 | 3 ms、**0% 丢包** | 物理链路和带宽正常 |
| `223.5.5.5` ICMP 15 包 | 40 ms、0% 丢包 | 同上，出境前也正常 |
| 网关 `192.168.0.1` ICMP | **86% 丢包** | **ICMP 限速假象**：同一条无线链路出去的 1.1.1.1 是 0% 丢包，不可能是链路在丢 |
| TCP 建连 `1.1.1.1:443` | 5 ms | WARP 隧道对端就是 Cloudflare，就近 |
| TCP 建连 `gitcode.com:443` | **249 ms** | **国内站正常应 <50 ms** —— 绕境外再回来的铁证 |
| TCP 建连 `github.com:443` | 103 ms / ICMP 13% 丢包 | 出境链路本身正常范围 |
| 网卡 | `WLAN` 协商 866.7 Mbps（`以太网 2` 已不在 Up 列表） | 本轮中途从网线换成了 WiFi |

**可复用规则**：
1. 判"被限速"必须**分层**——ICMP 丢包（可能被路由器/目标端限速，不可单独作证据）、TCP 建连延迟、TLS+首字节、吞吐，四层分开量。
2. **给国内站建连定基线：`<50 ms` 才算直连**。测出 200 ms 以上就先怀疑"被隧道拐走"，而不是怀疑运营商。
3. 网关 ICMP 丢包率异常时，用**同一链路出去的公网目标**做对照组；对照组 0% 丢包即可判"路由器 ICMP 限速"，别去重装驱动。
4. 纠错一条：本会话前一轮我写过"gitcode 直连 0.3–0.5 s 挺快"，那是**绕境外之后的绝对值**，没有基线对照就下了"快"的结论——
   以后判延迟一律先给"该目标应有的量级"，再比。

## 复核更正（2026-10-15 同日，A/B 跑完）：**WARP 不是吞吐低的主因，上面那条"主嫌"结论要降级**

做完 A/B 后推翻了自己：WARP **断开前后**同一国内镜像实测 6.0 Mbps → 5.3 Mbps，**没有变化**；
断开后出口 IP 变成 `61.187.10.74 / AS4134 CHINANET`（真实电信出口），DNS 回到 `1.1.1.1/8.8.8.8`，
`0.0.0.0/5` 分片路由数归零。⇒ **「绕境外一圈」是真的（`gitcode.com` TCP 建连 249 ms 是证据），但它不是这次下载慢的原因。**

真正的两个原因（都有数）：

1. **网卡只协商到 100 Mbps**：`Get-NetAdapter` 显示 `以太网 2 = 100 Mbps / FullDuplex=True / 0 错误计数`，
   而这块卡是 Realtek **2.5GbE**。2.5G 口掉到 100M 通常是网线只通 4 芯/水晶头氧化，或对端 LAN 口只有百兆。
   ⇒ 上限被砍掉 90% 以上，先修这个。
2. **源站按连接/IP 限速**：同一台 `mirrors.aliyun.com`，1→3→6 条并发实测 0 / 15.0 / 20.2 Mbps（单流约 5 Mbps 封顶，多流才叠得起来）；
   IDM 对 23.8 GB 那个任务开了 8 线程也只有 629 KB/s ≈ 5 Mbps ⇒ 多线程在该源上没有叠加效应，换网线也救不了这个任务。

**方法论教训（下次照做）**：
- 测速必须**分层 + 多流并发**：单流数字既可能是链路也可能是服务器按连接限速，只有并发叠加曲线能分开这两者。
- 做 A/B 前**必须先确认基线状态**：本次"关之前"的快照其实已经是断开状态（用户手动断过），
  差点让我把"同一条件测两遍"当成对照。⇒ 每次 A/B 的第一行输出要是被测组件自己的状态（这里是 `warp-cli status`）。
- 别把"我观察到的相关性"写成"主嫌"就交付；本轮我据此下过一次错误结论。

## 补充：2026-11-13 复核——出口是 WLAN；原「Radmin 抢路」判定因判据不足降级为未证实

**本节是复核更正，不是新故障。** 本机网络环境已变（2026-10 网关 `192.168.0.1`、WLAN 曾在 `192.168.171.231` → 现 WLAN 网关 `192.168.226.214`），历史值不可照搬。

### 实测（只读；`G:\AIrenwu\脚本库\04_规则审计\audit-snapshot.ps1` / `audit-probe2.ps1` / `audit-probe3.ps1` / `audit-probe4.ps1`）

- `Find-NetRoute -RemoteIPAddress 8.8.8.8` → 本机 IP `192.168.226.18`、ifIndex=19（**WLAN**，MediaTek Wi-Fi 6E MT7922，协商 866.7 Mbps）、下一跳 `192.168.226.214`。**真实出口是 WLAN，不是 Radmin。**
- 默认路由仅两条：WLAN `RouteMetric=0 + InterfaceMetric=35`（有效 35）；Radmin `RouteMetric=9256 + InterfaceMetric=1`（有效 9257）。Radmin 仍 Up、接口 metric 仍是 1，但路由层 9256 让它赢不了。
- `以太网 2`（当时的真实 uplink，Realtek 2.5GbE）现已 **Disconnected**（0 bps），InterfaceMetric=75。
- **WARP 未接管**：`warp-cli status` → `Disconnected / Reason: Manual Disconnection`（手动断开）；`Mode: Warp` 配置仍在、服务 `CloudflareWARP` 仍 Running/Automatic，但分片前缀路由（`0.0.0.0/5` 等）为 0、DNS 无 `127.0.2.x`、`Get-NetAdapter -IncludeHidden` 也无 WARP 适配器。⇒ 2026-10-15「WARP 接管全网」的状态已不存在；若日后重新连接 WARP，分片路由会回来，本节查法仍适用。

### 判据更正（本次复核的核心）

原记录判「Radmin 抢走默认路由」只凭 `Get-NetRoute` 表序（metric=1 居首）+ `Get-NetIPInterface`，**没有用 `Find-NetRoute` 实证出口**，也没有复现任何故障（原验证记录自标「实际影响验证：未做」）。按有效 metric = `RouteMetric + InterfaceMetric`，原记录自己证据表里的数字（Radmin 9256+1=9257 vs 以太网 2 0+35=35）就不支持「Radmin 赢」。

⇒ 原结论降级为**未证实（疑似表序误判）**；原文「决定胜负的是 InterfaceMetric，不是 RouteMetric」「前者通常是决定性的」**撤回**——2026-11-13 实测恰是 RouteMetric（9256）决定胜负的实例。两条后出记录与本复核一致：杀软断网修复（2026-10-31）与手动 DNS 冷解析（2026-11-06）都记「WLAN metric 35 出口 / Radmin 9257」。

**模式警告仍然成立**：Meta Tunnel 案例（上一条记录）有 Find-NetRoute 实证 + 真实故障 + 改 metric 前后对照，「空/极低 metric 虚拟网卡可能抢路由」仍是真实模式；但**判出口必须用 Find-NetRoute（或消费者侧实证），不能凭路由表序或单看接口 metric**。

### 其他过时项与剩余风险

- 代理选型节同样过时：「Clash(7897) 是唯一出境口」为当时实测；本机代理现为 **FlClash**（`D:\FlClash\FlClashCore.exe`，监听 7890），7897 无监听，系统代理 `ProxyServer=127.0.0.1:7890`。WARP 两层串联判据（分别量「走代理」和「直连」）仍有效。
- Radmin 接口 metric 原为 1（若重连并重建低 RouteMetric 默认路由可能再次抢路，推断未实测；现行路由层 9256 的缓解是谁设置的未知）。**2026-11-13 已提权修复**：会话内直接执行被「拒绝访问」后，经用户点击 UAC 提权执行 `Set-NetIPInterface -InterfaceIndex 8 -InterfaceMetric 5000` 成功（worker 内 fltmc=0 确认管理员）；改后 `Find-NetRoute 8.8.8.8` 复核出口仍 WLAN（192.168.226.18 / ifIndex=19），ActiveStore 与 PersistentStore 双存储回读均 5000（重启不弹回）。剩余风险收窄为：Radmin 客户端自身若重连时重写 metric，仍可能复发（未实测）。
- WARP 为手动断开，用户若重新连接，分片前缀接管会回来（2026-10-15 节的判据仍适用）。

## 关联

- 相关记录：[[踩坑-虚拟网卡空metric抢走默认路由致域名假超时]]（**本条是它的接力/状态更新**，
  模式相同、网卡已换；修复方法与判据链沿用该条）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：`Get-NetRoute -DestinationPrefix '0.0.0.0/0'`、
  `Get-NetIPInterface -AddressFamily IPv4 | Sort-Object InterfaceMetric`
