---
title: "冷解析 12 秒的真凶是非默认网卡上写死的手动 DNS 被 Windows 当默认服务器；判据是 nslookup 打印的 Server 行，不是 ipconfig"
date: 2026-11-06
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: high
stack: [Windows 11 28000, Dnscache, Radmin VPN, PowerShell, 批处理, Clash Verge]
tags: [DNS选路, 冷解析, 手动DNS, ResetServerAddresses, netstat假阴性, call参数赋值, 分层取证]
---

# 问题：网页"时快时慢"——同一个域名第二次 0.007 秒，第一次要 12 秒

## 一句话结论

本机某个网卡（Radmin VPN）上**写死**了 `NameServer=192.168.0.1,192.168.40.187`，这两个地址根本不应答，
而 **Windows 的 DNS 客户端把它当默认解析服务器用**：每个未缓存域名先在这上面耗掉一整轮重试（实测 **12.0 秒**）
才回落到能用的服务器。清掉之后同一测量是 **5~29 毫秒**。
判据不是 `ipconfig`（它按网卡列，看不出"系统实际先用谁"），而是 **`nslookup` 不带服务器时打印的那两行**：

```
服务器:  UnKnown
Address:  192.168.0.1          <-- 系统真正在用的那台，这里暴露了
```

配合一条对照就够定性：`Resolve-DnsName -Name X -Type A`（走系统选路）12,053ms
vs `Resolve-DnsName -Name X -Type A -Server 192.168.55.131 -DnsOnly` **5ms**。
**同一台机器、同一个名字、唯一差别是指不指定服务器** ⇒ 故障在"选路"，不在服务器、不在链路、不在本机防火墙。

## 触发条件与影响

- 环境与版本：Windows 11 10.0.28000，多网卡（WLAN 默认出口 metric 35 / Radmin VPN metric 9257 / 以太网2 断开 / VMware×2 / TUN）。
- 触发条件：网卡上留有**手动** DNS（注册表 `HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\<GUID>\NameServer`），
  而那个地址在当前网络里不可达。切换网络/热点后最容易复发。
- 影响范围：**每个新域名的第一次访问**慢 12 秒；已缓存的完全正常 ⇒ 表现为"第一次打不开、刷新就好了"。
  连带影响自动化：任何超时小于 12 秒的探测（`curl -m 8`）都会报"域名解析失败"，
  进而把排查者推向"IP 层坏了"的错误结论（本轮 `fix-network.bat` 就有这个连锁误判，已一并修掉）。

## 复现步骤

1. 前置：某非默认网卡有手动 DNS 指向不可达地址（本机 `192.168.0.1`）。
2. 操作：`ipconfig /flushdns`，然后 `nslookup www.sogou.com`（不带服务器参数）。
3. 预期：毫秒级返回。
4. 实际：`DNS request timed out. timeout was 20 seconds.` ×4，墙钟 100 秒；
   `Resolve-DnsName` 走系统选路 12.0s，加 `-Server` 后 5ms；
   原始 UDP 直接问 `192.168.0.1:53` 是 2.5s 超时，问 `192.168.55.131:53` 是 **4ms**。

## 证据

- `02_证据日志\冷解析归属判别.txt`：A) 同进程连解 5 个新名字，只有未缓存的慢；B) 每名字独立进程全部 12.0s；
  C) 热缓存 5~12ms；D) `getaddrinfo` 12,035ms 对同名字原始 UDP 6ms。
- `02_证据日志\dns截断与TCP53判别.txt`：TC 位全 False、答案包 90~489 字节 ⇒ **排除截断退 TCP** 这条常见猜测；
  顺带量到**路由器 TCP:53 不应答**（`TCP 无长度前缀`），公网 223.5.5.5 的 TCP:53 正常。
- `02_证据日志\死DNS修复AB-第二版.txt`：逐服务器可达性（192.168.0.1 / 192.168.40.187 FAIL 2.5s，其余 OK）
  → 清掉 idx8 后 `www.sogou.com=29ms www.maoyan.com=5ms www.csdn.net=5ms www.hupu.com=6ms`（改前全是 12,0xx ms）。
- `02_证据日志\冷路径复现.txt`、`dns_cold_probe.txt`：12 站点冷路径计时与四台 DNS 分层耗时。
- `02_证据日志\fix-network-v2.1-部署实测.txt`：工具实测输出。

## 根因分析

- 已确认的根因：非默认网卡上的**手动** DNS 不可达，被系统选路当默认服务器；12 秒是 Dnscache 的重试节奏。
- 排除过的假设（都留了实测）：
  - ~~DNS 服务器本身慢~~：原始 UDP 问同一台 4~46ms。
  - ~~IPv6 优先导致回退~~：本机只有链路本地 `fe80::`，无全局 IPv6、无 `::/0` 路由；`curl -4` 与 `-6` 对照过。
  - ~~UDP 截断后退 TCP:53 卡住~~：TC 位全 False（虽然路由器 TCP:53 确实不应答，但没触发）。
  - ~~hosts 文件 / 后缀搜索 / devolution~~：hosts 836 字节无相关条目；`SuffixSearchList` 空，只有 以太网2 有 `lan` 后缀。
  - ~~杀软 LSP~~：`netsh winsock show catalog` 无第三方条目。
  - ~~`-State Listen` 那类状态判据~~：见下面"附带发现 2"，同一个坑的另一种表现。
- 问题归属：**修改前已有**（历史遗留的手动值），本次由排障暴露。

## 最小修复

```powershell
# 只对"探测确认不应答 + 是手动值 + 不是默认出口网卡"三者同时成立的接口执行
Set-DnsClientServerAddress -InterfaceIndex 8 -ResetServerAddresses
```

- `-ServerAddresses @()` 是**空操作**（改后回读和改前一模一样），我第一次就是这么"修完"却没变化还以为假设错了；
  要恢复 DHCP 下发必须用 `-ResetServerAddresses`。
- 默认出口网卡的 DNS 即使不应答也**不碰**：清掉等于一个都不剩。
- DHCP 下发的不应答地址**不碰**：清了下次还是它，要去改路由器（本机 以太网2 现在就是这种，已如实报出）。
- 改前原值与还原命令一并打印并落日志，可一键回滚。

## 验证记录

- [x] 逐服务器原始 UDP 探测：死/活分类与 `nslookup` 暴露的"系统实际在用谁"一致
- [x] 清 idx8 后冷解析 12,0xx ms → 5~29 ms；`nslookup` 默认服务器变成 `192.168.55.131` 且立即出答案
- [x] 端到端消费者视角：`curl` 直连 qq 0.68s、经 7897 github 1.24s（改前 3.3~5.2s）
- [x] 幂等与边界：再跑一次探针报"各网卡登记的 DNS 都会应答"；对 DHCP 来源的死地址只报不改
- [x] 工具层：`fix-network.bat v2.1` check/fix 两种模式在隔离副本与部署位置都跑通，输出对齐
- [ ] 未验证：12 秒这个具体数字是否恒为 12（与 Dnscache 重试节奏相关，只在本机量到 12.0~12.1，未跨机器验证）

## 附带发现（同一条排障链上的三个工具坑）

1. **`netstat` 在本机把 mihomo 的监听套接字报成 `CLOSED`**，所以 `netstat | findstr LISTENING` 判端口是假阴性
   （和 `Get-NetTCPConnection -LocalPort N -State Listen` 恒回空是同一个毛病的两种表现）。
   判端口死活唯一可靠的是**真的连一次**：`TcpClient.BeginConnect('127.0.0.1',N)` + `WaitOne(1200)`。
2. **`call :label a=b` 会被 cmd 当成变量赋值吃掉**，子过程收到的参数整体前移（`%1`=`ip`、`%2`=`192.168.55.131`），
   于是解析结果一片乱码却**不报任何错**。子过程实参一律加引号：`call :sub "%%A" "%%B"`。
3. **`powercfg /q` 的无线节能那次改动其实没落地**：我的 GUID/标签解析没匹配上，脚本自己打印了"本次不改"，
   前后两轮延迟 3.42s / 3.63s 无差异——**不能当成"优化过网卡节能"的证据**，网卡节能仍是未动项。

## 可复用规则

1. 判"解析慢"先做**一条对照**：`Resolve-DnsName X` vs `Resolve-DnsName X -Server <那台>`。
   差一个 `-Server` 就是选路问题，别再往服务器/链路上找。
2. 想知道"系统实际在用哪台 DNS"，用 **`nslookup 不带服务器参数`**，看它打印的 `Address:` 行；
   `ipconfig`/`Get-DnsClientServerAddress` 只能告诉你每张网卡**各自登记**了什么。
3. 手动 DNS 的真值在 `Interfaces\<GUID>\NameServer`；判"是不是本机写死"要读这个键，不要靠界面猜。
4. 清手动值只用 `-ResetServerAddresses`；`-ServerAddresses @()` 静默无效。
5. 判端口在不在听：**连一次**，别信状态字符串（`netstat`/`-State Listen` 在本机都会骗人）。
6. 探测工具的超时必须大于"最坏冷解析时间"，否则工具自己会造出"IP 层坏了"的假结论并触发无谓的 DHCP 重取。

## 适用范围与不适用范围

- 适用：Windows 多网卡（VPN/TUN/虚拟适配器）机器上"偶发慢、刷新就好"的解析问题；批处理调用 PowerShell 解析结构化输出。
- 不适用：单网卡 DHCP 环境（没有"另一张网卡的写死值"可抢）；程序自带 DNS（如浏览器 DoH、`--dns`）时系统选路不参与；
  macOS/Linux 无 Dnscache 这套重试节奏。

## 本机痕迹

- 被清掉的值（还原命令）：`Set-DnsClientServerAddress -InterfaceIndex 8 -ServerAddresses 192.168.0.1,192.168.40.187`
  （GUID `{4b4a4c14-4f80-4b9a-b6ac-de9bd2542497}`，留档 `02_证据日志\死DNS归属AB-改前NameServer留档.json`）
- 工具升级：`E:\DeskBox\VPN\fix-network.bat` v2.0(438 行/16,151B) → **v2.1(681 行/25,555B)**，
  新增同级探针 `E:\DeskBox\VPN\fix-network.dns.ps1`(6,990B)；
  原件备份 `G:\AIrenwu\03_备份\DeskBox-原件备份-20261106\VPN\fix-network.v2.0.bat`（sha256 前 12 位 `e82f32dca824`，与原件逐字节一致）。
- 脚本与日志：`G:\AIrenwu\01_任务归档\2026-11-03_后台进程盘点\03_工具脚本\{cold_dns_attribution,dns_cold_probe,dns_truncate_probe,cold_path_repro,dns_srv_probe}.py`、
  `{dns_dead_fix_ab2,dns_which_server,net_stability_readonly,net_stability_readonly2,optimize_wifi_power,patch_fix_network,patch_fix_network2,patch_fix_network3}.ps1|.py`；
  取证在 `02_证据日志\`。
- 仍未动：网卡节能（`LowPowerEnable=Auto`、`RoamIndicateTh=5.中高`）、路由器 TCP:53 不应答、
  `192.168.0.1` 这个 DHCP 下发死地址（在断开的 以太网2 上，本机改不动）。
