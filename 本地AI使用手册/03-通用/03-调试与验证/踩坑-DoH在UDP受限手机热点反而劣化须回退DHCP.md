---
title: "DoH 在 UDP 受限的手机热点上反而劣化，须回退 DHCP"
date: 2026-11-11
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Windows, DNS, DoH, 手机热点]
tags: [DNS, DoH, 热点, 超时]
---

# 问题：DoH 在 UDP 受限的手机热点上反而劣化，须回退 DHCP

## 一句话结论

在 UDP 被限速/丢包的手机热点上给 DNS 开 DoH（autoupgrade）会把冷解析拖到 27–32 秒；回退 DHCP（路由器 DNS）后 36–74ms。DoH 不是默认优化。

## 触发条件与影响

- 环境：Windows 11，WLAN 接手机热点（网关只开 TCP 53，公网 ICMP/UDP 大量丢包）。
- 触发：`netsh dns add encryption server=223.5.5.5 dohtemplate=https://dns.alidns.com/dns-query autoupgrade=yes udpfallback=yes` + 设 WLAN DNS 为 223.5.5.5/223.6.6.6。
- 影响：新域名冷解析 27–32s，浏览器/Qoder 明显卡。

## 复现步骤

1. 前置：热点链路，原始 UDP DNS 16 次仅 1 次成功。
2. 操作：加 DoH 模板 + 手动 DNS → `ipconfig /flushdns` → 计时 `getaddrinfo`。
3. 预期：DoH 提速。
4. 实际：27–32s；回退后 36–74ms。

## 证据

- 加 DoH 后 `www.codebuddy.cn`/`gitcode.com` 解析 27–32s（2026-11-11 实测）。
- `netsh dns delete encryption server=223.5.5.5/223.6.6.6` + `Set-DnsClientServerAddress -ResetServerAddresses` 后同域名 36–74ms。

## 根因分析

- 已确认：DoH 引导仍需先解析 DoH 主机名，走被限速的 UDP，先 stall 再回落，整体更慢。
- 排除：DNS 服务器本身慢（回退后快）。
- 归属：环境（热点 UDP 受限）× 配置（DoH）叠加。

## 最小修复

- 删除 DoH 模板 + 重置 WLAN DNS 为 DHCP。

## 验证记录

- [x] 回退后冷解析 36–74ms，多域名复测一致。

## 可复用规则

- 热点/UDP 受限环境先测**原始 UDP DNS** 成功率，再决定要不要 DoH；DoH 劣化就回退，别当默认优化。
- 判 DNS 慢要分层计时（DNS/TCP/TLS/TTFB），只有 DNS 段秒级才是解析器问题。

## 适用范围与不适用范围

- 适用：UDP 被限速/丢包的热点、校园网等。
- 不适用：UDP 正常的宽带（DoH 可能有益）。

## 剩余风险

- 不同热点 UDP 策略不同，需现测。

## 关联

- [[踩坑-虚拟网卡空metric抢走默认路由致域名假超时]]
- [[踩坑-MediaTek WLAN扩展mtkwlex卸载重载致Wi-Fi硬断手机正常电脑断]]
