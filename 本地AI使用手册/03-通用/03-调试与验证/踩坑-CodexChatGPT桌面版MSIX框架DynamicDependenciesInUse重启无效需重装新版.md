---
title: "Codex/ChatGPT 桌面版 MSIX 框架 DynamicDependenciesInUse，重启无效，重装新版修复"
date: 2026-11-24
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: high
stack: [MSIX, Appx, OpenAI Codex, ChatGPT, Windows, winget, BITS]
tags: [MSIX, 0x800701C0, 0x80073D3C, 0x80073D02, DynamicDependenciesInUse, NotAvailable, 延迟删除, 框架包, Codex, ChatGPT, 重装]
---

# 问题：Codex/ChatGPT 桌面版起不来，0x800701C0「配置运行时遇到错误」

> `verified`：根因证实，且**重装最新版 MSIX 后已成功启动并验证窗口可见**。重要更正：单纯注销/重启**并不能**修复本例（与最初假设相反）。

## 一句话结论

「GPT」实为 OpenAI Codex 桌面版（MSIX 包 `OpenAI.Codex_2p2nqsd0c76g0`，主程序 `app/ChatGPT.exe`，winget 名 `OpenAI.ChatGPT`）。其运行时框架包 `OpenAI.CodexPrimaryRuntime.v26-1119-907-0` 卡在 `NotAvailable`，被「动态依赖占用」（`DynamicDependenciesInUse`）标记，主程序启动报 `0x800701C0`。**重启、停服务、重注册、Remove 全无效**；最终靠**重装更新版应用**（26.1120.5083.0，带来新框架家族 `v26-1123-915-0`）绕过损坏的旧框架家族而修复。

## 触发条件与影响

- 项目或功能：OpenAI Codex / ChatGPT 桌面版（MSIX，开机自启项 `Startup\OpenAI Codex.lnk` → `explorer.exe shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App`）。
- 环境与版本：旧主包 `OpenAI.Codex_26.1111.9664.0_x64__2p2nqsd0c76g0`（SignatureKind=Store）；旧框架 `OpenAI.CodexPrimaryRuntime.v26-1119-907-0_26.1119.907.0_x64__3k8sg7r9htsxt`（IsFramework=True, SignatureKind=Developer）Status=NotAvailable。Windows 10.0.28000。
- 触发条件：框架包被持久「动态依赖 pin」（MSIX package graph / `AddPackageDependency`）标记占用，进入延迟删除/损坏态。
- 影响范围：Codex/ChatGPT 桌面版完全无法启动。

## 证据

- `Microsoft-Windows-AppModel-Runtime/Admin` 事件反复 `0x800701C0`「无法为程序包…创建桌面 AppX 容器，因为在配置运行时的过程中遇到错误。[LaunchProcess]」。
- `Get-AppxPackage`：主包 Status=Ok；框架 Status=NotAvailable（PackageUserInformation={Admin:Installed}，InstallLocation 文件夹完整：AppxManifest.xml、runtime.json、AppxBlockMap.xml、plugins、dependencies）。
- 重注册框架 `Add-AppxPackage -Register … -DisableDevelopmentMode -ForceApplicationShutdown` → `0x80073D3C`「程序包正在等待删除，请注销并重新登录」；AppPackageLog「错误 0x80073D3C：Resolved 状态处理程序失败 / Failed to reach state Resolved」。
- `Remove-AppxPackage`（含 `-AllUsers`）/`Reset-AppxPackage` → `0x80073D02`，部署日志具体处理器＝**「DynamicDependenciesInUse 状态处理程序失败」**（关键根因线索）。
- Sysinternals `handle64.exe` 扫 `CodexPrimaryRuntime` → 「No matching handles found」⇒**无任何进程持文件句柄**，占用是 StateRepository 里的持久动态依赖标记，不是文件锁。

## 根因分析

- 框架包被「动态依赖」持久 pin 住 → NotAvailable/延迟删除态 → 主程序配置运行时失败 0x800701C0。
- **该状态极顽固**：重启机器、`Restart-Service StateRepository -Force`+AppXSvc、停 `CodexSandboxService.OpenAI.Codex`、各种 `-Force*` 重注册参数，全部仍 0x80073D3C。
- 排除：① 主包损坏（Status=Ok）；② 框架文件缺失（InstallLocation 完整）；③ 进程占用（handle64 无句柄）；④ AppXSvc 停摆（Running）。
- 与全局记忆 `reference-claude-desktop-msix-launch.md`（0x80070020 注销/重启可解）**不同**：本例重启无效，必须换框架家族。

## 最小修复（已验证）

核心思路：**别再修旧框架，重装更新版应用，让它带一个新框架家族绕过损坏态。**

1. 查最新版：`winget show --id OpenAI.ChatGPT`（本机命中 26.1120.5083.0，安装程序类型 msix，URL `https://persistent.oaistatic.com/codex-app-prod/releases/<ver>/ChatGPT-x64.msix`，约 734MB，含 SHA256）。
2. 稳健下载（winget 长下载易被中断 0x800704C7）：用 **BITS** 服务级持久下载，进程死也续传：
   ```powershell
   Start-BitsTransfer -Source $url -Destination 'G:\AIrenwu\ChatGPT-x64.msix' -DisplayName ChatGPTmsix -Asynchronous -Priority Foreground
   # 轮询 Get-BitsTransfer -Name ChatGPTmsix；JobState=Transferred 后 Complete-BitsTransfer 落盘
   ```
3. 校验 SHA256 与 winget 公布值一致。
4. **提权**安装（MSIX 需管理员，非提权报 0x80073d28）：
   ```powershell
   Add-AppxPackage -Path 'G:\AIrenwu\ChatGPT-x64.msix' -ForceApplicationShutdown
   ```
5. 启动：`Start-Process explorer.exe 'shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App'`。

注意：Store 签名包**不能**从松散备份目录重注册（`Add-AppxPackage -Register <备份>\AppxManifest.xml` 报 0x80073CF9「manifest 没有位于程序包根目录」），所以「先 Remove 主包再从备份 Register」这条路走不通，务必走 .msix 重装。

## 验证记录

- [x] 根因定位：0x800701C0 + 框架 NotAvailable + 重注册 0x80073D3C + Remove 0x80073D02 DynamicDependenciesInUse + handle64 无句柄，互证。
- [x] 重启无效实证：用户重启后 RunOnce 自动重注册 5 次仍 0x80073D3C，框架仍 NotAvailable。
- [x] 修复回归：重装 26.1120.5083.0 后 `Get-AppxPackage` 主包 Status=Ok、新框架 `OpenAI.CodexPrimaryRuntime.v26-1123-915-0` Status=Ok；旧损坏框架 v26-1119-907-0 已消失；非提权激活后 EnumWindows 见可见窗口「ChatGPT」，进程树含 codex-code-mode-host / codex-computer-use-swift / codex-windows-sandbox-service，近 5 分钟无 AppModel 错误。

## 可复用规则

- MSIX 应用启动报 0x800701C0「配置运行时错误」：先 `Get-AppxPackage` 查依赖框架 Status；NotAvailable 且重注册报 0x80073D3C 时，**先试注销/重启，但若 Remove 报 0x80073D02 DynamicDependenciesInUse 且 handle64 无句柄，说明是持久动态依赖损坏态，重启往往无效——直接重装更新版应用换新框架家族最稳**。
- 大 MSIX 下载用 BITS（服务级、可续传、抗进程中断），别依赖 winget 一次性长下载；安装需提权。
- 判「GPT/ChatGPT 桌面版」是哪个程序：查启动项 lnk 的 AUMID（`shell:AppsFolder\<PackageFamilyName>!App`），本机实为 OpenAI.Codex 包内 ChatGPT.exe；winget 包名 OpenAI.ChatGPT。
- 提权进程里启动的 GUI 可能不在普通桌面可见；验证窗口要在**用户会话非提权**再激活一次并用 EnumWindows 确认。

## 适用范围与不适用范围

- 适用：MSIX/Desktop AppX 应用因框架包动态依赖损坏/延迟删除致启动失败，且重启无效者。
- 不适用：非 MSIX 程序（如 PixPin，另见 [[03-通用/03-调试与验证/踩坑-PixPin启动即崩0xC0000409因截图历史索引损坏改名即修复|PixPin 条]]）；框架文件真缺失（直接重装即可）。

## 剩余风险

- 重装会升级到新版（界面/功能可能变化）；若必须保留旧版，需先彻底清理旧框架家族（可能仍需注销/重启或 StateRepository 层面处理，风险高）。
- 下载源 oaistatic.com 在国内可能慢，BITS 前台优先级实测约数 MB/s。

## 关联

- 相关记录：[[03-通用/03-调试与验证/踩坑-PixPin启动即崩0xC0000409因截图历史索引损坏改名即修复|PixPin 启动即崩 0xC0000409]]（同日另一程序起不来，根因不同）。
- 全局记忆：`reference-claude-desktop-msix-launch.md`（同类 MSIX 启动死锁，但本例重启无效，结论需区分）。