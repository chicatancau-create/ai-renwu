---
title: "虚拟网卡空 InterfaceMetric 抢走默认路由，表现为某些域名直连超时"
date: 2026-10-11
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: high
stack: [Windows, Wintun, PowerShell, NetAdapter]
tags: [网络取证, 路由, 假超时]
---

# 问题：某域名直连一律 `CONNECT_TIMEOUT`，走代理就秒回——真凶是另一块虚拟网卡抢了默认路由

## 一句话结论

一块 `AutomaticMetric=Disabled` 且 **`InterfaceMetric` 为空** 的 Wintun 虚拟网卡（本机是 `Meta Tunnel`，
Meta 系 App 建的）会以最高优先级抢走默认路由，把流量灌进隧道；某些目标在隧道里连得上但不回数据，
于是客户端只看到「连接超时」。**这不是 DNS 污染，也不是目标站挂了，也不是链路丢包。**
把它的 `InterfaceMetric` 调大（本机 5000）即可，不用禁用网卡。

## 触发条件与影响

- 环境与版本：Win11 28000；Wi-Fi 断开中；另有 RNDIS 虚拟网卡（`192.168.134.34`，网关 `.241`，通常是手机 USB 共享）在当实际 uplink。
- 触发条件：装了带 VPN/TUN 的桌面 App（Meta / 各类加速器），主用网卡断开后它成了唯一「Connected」的默认路由。
- 影响范围：所有不走系统代理的程序（Rust/Node/Electron 自带 HTTP 栈的客户端尤其明显）。

## 复现步骤

1. 前置条件：主用网卡断开，存在一块空 metric 的 TUN 网卡。
2. 操作或命令：`node -e "fetch('https://<目标>/v1/messages', …)"`（不设任何代理）。
3. 预期结果：秒回。
4. 实际结果：`UND_ERR_CONNECT_TIMEOUT`，10.5–15 s，3/3 全挂；同一时刻 `Test-Connection 223.5.5.5` 却是 True（因为通用站点在隧道里能用）。

## 证据

- `Find-NetRoute -RemoteIPAddress <目标IP>` → `InterfaceAlias: Meta / IPAddress: 198.18.0.1`（**出口被隧道接管**，连私网地址都从隧道出）。
- `Get-NetIPInterface -InterfaceIndex 4` → `InterfaceMetric` 为**空**、`AutomaticMetric: Disabled`。
- 对照：`ping 192.168.91.113`（路由器）False，但 TCP 连它 80/443「可连」——查 `Get-NetTCPConnection` 发现源地址是 `198.18.0.1`，
  **那个"可连"是隧道另一端在答，不是路由器**。用 TCP 可连反证"网关通"是错的。
- 改后：`Set-NetIPInterface -InterfaceIndex 4 -InterfaceMetric 5000` → 出口变为 `192.168.134.34`；
  同一把 key 同一命令 **3/3 HTTP 200，2.0–3.5 s**；`www.qq.com` 0.4 s、`223.5.5.5` 0.2 s。

## 根因分析

- 已确认的根因：默认路由优先级由 `InterfaceMetric + RouteMetric` 决定；空值按最低（最优先）处理，
  于是 TUN 压过实际 uplink（本机 RNDIS 是 75）。
- 排除过的假设：DNS 污染（Google DoH 与系统解析同 IP，已证伪）；目标站封锁（走代理秒回）；本机防火墙（无拦截记录需求）。
- 问题归属：环境或依赖（第三方 App 建的虚拟网卡）。

## 最小修复

```powershell
# 需要管理员
Set-NetIPInterface -InterfaceIndex 4 -InterfaceMetric 5000   # 只降优先级，不删网卡不删路由
```

**不要顺手禁用那块"看着多余"的 RNDIS/ICS 网卡**——本次它恰恰是真正的 uplink，禁了就全网中断。
禁用 TUN 网卡也可能把依赖它的 App 弄挂；降优先级是可逆且副作用最小的做法。

## 验证记录

- [x] 改前基线：目标域名直连 3/3 超时（带耗时）。
- [x] 改后同一命令：3/3 HTTP 200（2.0–3.5 s）。
- [x] 出口归属变化：`Meta/198.18.0.1` → `以太网/192.168.134.34`。
- [x] 通用连通性未受损：`223.5.5.5` 0.2 s、`www.qq.com` 200。
- [ ] 重启后是否仍保持 5000：未测（建卡的那个 App 可能改回去）。
- [ ] Wi-Fi 重连后三块网卡的优先级排序：未测（Wi-Fi 目前仍断开）。

## 可复用规则

客户端报「连不上某域名」但浏览器/代理能上时，按这个顺序查：
① `Find-NetRoute -RemoteIPAddress <IP>` 看出口是哪块网卡 →
② `Get-NetIPInterface` 看各卡 `InterfaceMetric` 有没有空值/异常低值 →
③ 判"网关是否真的可达"必须看 `Get-NetTCPConnection` 的**本地地址属于哪块网卡**，
   不能只看 TCP 能连上（隧道会替你应答）。

## 适用范围与不适用范围

- 适用：Windows 上任何装了 TUN/VPN/加速器虚拟网卡的本机。
- 不适用：代理端出口质量差导致的超时（那要换节点，不是改本机 metric）。

## 剩余风险

建卡的 App 更新或重启可能重置 metric；若哪天真的需要走 Meta 隧道，这个改动会让它不再自动接管，
需要手动把 metric 调回（`Set-NetIPInterface -InterfaceIndex 4 -InterfaceMetric 1`）。

## 关联

> **⚠️ 本条的网卡名已过时（2026-10-13）**：抢默认路由的已不是 `Meta Tunnel`，
> 而是 **`Radmin VPN`（`InterfaceMetric=1`、`AutomaticMetric=Disabled`）**。
> **模式、判据链与修复方式仍然有效**，但请勿凭本条认定网卡名——见接力记录
> [[规则-默认路由抢占网卡已换为RadminVPN]]。
> **2026-11-13 再复核**：Radmin 也不再抢路——其默认路由 `RouteMetric=9256`（有效 metric 9257），
> `Find-NetRoute -RemoteIPAddress 8.8.8.8` 实测出口为 **WLAN**（本机 `192.168.226.18`，网关 `192.168.226.214`）。
> 接力记录原判「Radmin 抢路」仅凭路由表序、未用 Find-NetRoute 实证，已在其 2026-11-13 补充节降级为「未证实」。

- 相关记录：[[踩坑-第三方Claude客户端自带服务商配置切全局路由无效]]（本条是它当时"必须走 7897"结论的真因修正）、
  [[规则-Windows新窗口默认居中只能常驻监视器]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
