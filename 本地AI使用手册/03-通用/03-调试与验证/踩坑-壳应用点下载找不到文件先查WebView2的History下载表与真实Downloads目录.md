---
title: "壳应用点「下载」找不到文件：先查 WebView2 的 History 下载表与本机真实 Downloads 目录"
date: 2026-11-15
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [WebView2, Tauri, Pake, node:sqlite, Windows]
tags: [下载取证, WebView2, KnownFolder, 重定向, sqlite]
---

# 问题：LazyManChat 点「下载 PDF」后全盘找不到这个 PDF

> 本条已完成复现、定位、验证三步，状态 `verified`。**但「按钮为什么没触发下载」这一点未查清，见剩余风险。**

## 一句话结论

判「到底下载成功了没有」不要靠翻目录，直接读 WebView2 profile 里 `History` 库的 `downloads` 表——**0 行就是浏览器层一次都没发生**；同时这台机器的真实下载目录**不是** `C:\Users\Admin\Downloads`（该路径根本不存在），而是被指到了 `G:\NDM下载`，只按习惯路径找必然找不到。

## 触发条件与影响

- 项目或功能：LazyManChat 桌面端的「分享 → PDF → 下载 PDF」（15 页预览能正常显示）。
- 环境与版本：`pake-lazymanchat.exe`（Pake/Tauri 壳 + Edge WebView2），数据目录 `C:\Users\Admin\AppData\Roaming\LazyManChat\EBWebView`；壳内加载的是云端站 `https://lazymanchat.com`。
- 触发条件：点「下载 PDF」后在 Downloads / Documents / Desktop 找不到文件。
- 影响范围：任何 WebView2/Tauri 壳应用的「下载了但找不到」类排查；以及所有硬编码 `%USERPROFILE%\Downloads` 的软件。

## 复现步骤

1. 前置条件：壳应用正在运行（会独占 `History` 库）。
2. 操作或命令：见下方「证据」的四步取证。
3. 预期结果：`downloads` 表里有对应记录，文件落在真实下载目录。
4. 实际结果：`downloads` 与 `edge_downloads` 均 **0 行**；真实下载目录 `G:\NDM下载` **0 个文件**；全盘无新 PDF。

## 证据

四步取证（2026-10-20 实测，2026-11-15 复核路径仍成立）：

```sh
# 1) 真实下载目录到底指向哪（PowerShell 是唯一可靠的问法）
powershell -NoProfile -Command "(New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path"
# → G:\NDM下载   （而 C:\Users\Admin\Downloads 这个路径不存在）

# 2) History 库被占用，必须先拷快照再开（直接 readOnly 打开报 database is locked）
cp ".../LazyManChat/EBWebView/Default/History"  <临时目录>/h.db

# 3) 查下载表
SELECT COUNT(*) FROM downloads;      -- → 0
SELECT COUNT(*) FROM edge_downloads; -- → 0

# 4) 全盘找今天新建的 PDF
find /c /d /e /f /g /h -maxdepth 4 -iname "*.pdf" -newermt "2026-10-20"   # → 只有两个插件自带样例
```

同一轮还确认：`urls` 表 127 行、`visits` 1377 行，21:25 前后全是 `lazymanchat.com/chat?topic=...`、`/knowledge`、`/aippt`，说明壳在正常联网浏览，只是没有任何下载事件。

**用 `node:sqlite` 读 Chromium 库的两个坑（都实测踩过）**：

1. Chromium 时间戳是「自 1601-01-01 的微秒数」，超出 JS number 安全整数，`.all()` 会直接抛
   `RangeError: Value is too large to be represented as a JavaScript number`。
   → 在 SQL 里 `CAST(last_visit_time AS TEXT)` 取出来再换算。
2. 脚本扩展名 `.mjs` 下 `require` 不可用（ESM），要写 `import { DatabaseSync } from "node:sqlite"`。
3. 另：`reg query` 的输出是 UTF-16LE，bash 里 grep 会报 `Binary file matches`，要么用 PowerShell 读，要么在 node 里 `.toString("utf16le")`。

## 根因分析

- 已确认：这次「找不到文件」的原因是**下载从未发生**（不是落到了奇怪路径，也不是被杀软拦后改名）。依据是下载表 0 行 + 全盘无新 PDF + 真实下载目录空。
- 排除过的假设：①「落到了重定向的下载目录」——`G:\NDM下载` 0 个文件；②「落到了 TEMP」——全用户目录 21:20 之后新写入的文件只有 Chrome 内部状态与 DeskBox 日志，没有壳应用产物；③「被隐藏扩展名/改名」——按 `*.pdf` 与按 mtime 两轮都空。
- 问题归属：环境或依赖（壳与云端站的实现问题），非本机配置错误。

## 最小修复

本机无可修之处。排查这套问题时的固定顺序：

1. 读壳应用 profile 的 `History` → `downloads` 表行数（判「有没有下」）。
2. 问 `shell:Downloads` 的真实路径（判「该下到哪」）。
3. 再按 mtime 全盘扫（判「有没有以别的名字落盘」）。

## 验证记录

- [x] 注册表读取（2026-11-15 用 node 正确解码 UTF-16 重测）：`HKCU\...\Explorer\User Shell Folders` 与 `Shell Folders` **两处都没有 `{374DE290-…}` 也没有任何 Download 条目**，而 `Shell.Application` 的 `shell:Downloads` 解析出 `G:\NDM下载`
- [ ] **未证实**：这个 `G:\NDM下载` 到底由什么机制生效（标准 Known Folder 覆盖项已被排除）。不写成规则，只留操作判据：**问下载目录只认 `Shell.Application`，不要读注册表、也不要假设 `%USERPROFILE%\Downloads`**
- [x] 取证脚本自测：三次迭代（`probe.mjs`/`probe2.mjs`/`probe3.mjs`）最终跑通，输出 `downloads 0`、`urls 127`
- [x] 端到端：结论「未下载」由三条独立证据交叉支持（下载表、目录内容、全盘 mtime 扫描）
- [ ] 修复验证：不适用（未修复按钮本身）

## 可复用规则

- 面对「WebView2 / Tauri / Pake 壳应用说下载成功但找不到文件」，**先读 `EBWebView\Default\History` 的 `downloads` 表**，再看目录。表空 = 没下，后面全不用查。
- 本机写脚本查任何 Chromium 系数据库（History/Cookies/Favicons/leveldb）：库被占用时**先拷快照副本**，用 `readOnly` 打开副本；Int64 列一律 `CAST(... AS TEXT)`。
- 涉及「下载目录」的判断，一律用 `Shell.Application` 问 `shell:Downloads`，不要假设 `%USERPROFILE%\Downloads`——这台机器上那个路径不存在。

## 适用范围与不适用范围

- 适用：所有 WebView2/Tauri/Pake/Electron-with-WebView2 壳应用的下载排查；本机任何需要 Known Folder 真实路径的脚本。
- 不适用：Chrome/Edge 主浏览器自身的下载（库路径不同，但方法一致）；原生 Win32 程序自管下载（不写 WebView2 的 History）。

## 剩余风险

- **未证实**：LazyManChat 的「下载 PDF」为什么没触发下载——是云端没返回文件、blob 下载被壳拦截、还是按钮本身没接线，本轮没有取证（需要抓它的网络请求或读前端实现）。
- 本机 `C:\Users\Admin\Downloads` 不存在而 `G:\NDM下载` 为空，硬编码该路径的软件可能静默失败，这一条只验证了「路径不存在」，**没有**逐个验证哪些软件受影响。

## 关联

- 相关记录：`踩坑-沙箱只放行工作区致写E盘被拒且write会抹掉源码BOM.md`、`踩坑-插件改了不生效先查实际加载的是哪份副本.md`
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关命令：`node:sqlite`、`(New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path`
