---
title: "应用通知设置全开却不弹：真凶是组策略 NoToastApplicationNotification，不是 Notifications\Settings 里那个总开关；判据只有 ETW 的 PolicyReason"
date: 2026-11-06
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Windows 11 28000, Qoder Desktop, WpnService, WinRT Toast, ETW]
tags: [系统通知, 组策略优先, PushNotification-Platform, PolicyReason, WpnUserService, 假根因]
---

# 问题：Agent 每轮结束毫无提示；第一轮定位到的"根因"是错的，第二版才找到真凶（已 verified，端到端由 ETW 3153 证实）

## 一句话结论

**Windows 通知有至少三层开关，越靠上越硬**：组策略 `NoToastApplicationNotification` > 用户级 `PushNotifications\ToastEnabled` > `Notifications\Settings\NOC_GLOBAL_SETTING_TOASTS_ENABLED`。
只改最下面那个值，回读是 1、看着"改成功了"，但 toast 照样被丢——
**唯一能证明"为什么被丢"的是 ETW `Microsoft-Windows-PushNotification-Platform/Operational` 里的 `Id=3150 + PolicyReason`**，
不是注册表值，也不是应用设置。

## 触发条件与影响

- 环境：Windows 11 28000 + Qoder Desktop 0.5.5（`com.qoder.app`）
- 应用侧实测（`qoder-settings`，非默认值猜测）：`notification.turnMode = always`、`permissionRequestsEnabled = true`；
  目录里**没有任何提示音设置**（搜「声音」只有声纹，搜「sound」0 条）⇒ 声音由系统 toast 携带
- 系统侧真凶（2026-07-22 15:27 一批"隐私/去广告"策略写入，**谁写的未验证**）：
  ```
  HKCU\Software\Policies\Microsoft\Windows\CurrentVersion\PushNotifications
      NoToastApplicationNotification = 1      ← 拦截源
      NoTileApplicationNotification  = 1
  HKCU\Software\Microsoft\Windows\CurrentVersion\PushNotifications
      ToastEnabled = 0
  ```
  同批还有 `TurnOffWindowsCopilot=1`、`DisableWindowsSpotlight*`、`DisableAIDataAnalysis`、
  `DisableSearchBoxSuggestions`、WER `LoggingDisabled` 等 8 项（本次一律未动）
- 影响：所有应用的 toast 全被丢弃，且**应用侧完全不报错**——看起来像应用的通知功能坏了

## 我第一版为什么判错（值得记住的教训）

| 我的断言 | 实测反驳 |
|---|---|
| 「`NOC_GLOBAL_SETTING_TOASTS_ENABLED=0` 是根因」 | 改成 1 并回读成功后，15:34 我自己发的测试 toast **仍被 3150 GlobalSettingDisabled 拦下** |
| 「Qoder 从没成功注册过通知（子键列表里没有它）」 | ETW 明确有 `Id=2416 已收到` + `Id=2418 已提交线程池`，AppId=`com.qoder.app`——**它一直在发**，是系统丢的 |
| 「WpnUserService Stopped 是通知被关的旁证」 | 该服务是**按需启动**的；我自己 `sc stop` 之后它不自动回来，导致 `CreateToastNotifier` 抛「通知平台不可用」——是我制造的状态，不是原故障 |

教训：**注册表值"读到 1"不等于"策略生效"**；开关类问题要拿"事件级拒绝原因"定性，
并且要区分"我改动后的状态"与"原始故障状态"。

## 复现步骤

1. 前置：`HKCU\Software\Policies\...\PushNotifications\NoToastApplicationNotification = 1`
2. 操作：把 `NOC_GLOBAL_SETTING_TOASTS_ENABLED` 设为 1，然后发一条 toast
3. 预期：通知显示
4. 实际：ETW `Id=3150 PolicyReason [GlobalSettingDisabled]`，无显示；设置页的开关怎么点都没用

## 修复（本次实际做的）

```powershell
# HKCU\Software\Policies 对普通用户只读（默认 DACL：SYSTEM/Administrators 可写），必须提权
Remove-ItemProperty 'HKCU:\Software\Policies\Microsoft\Windows\CurrentVersion\PushNotifications' `
                   -Name 'NoToastApplicationNotification' -Force
Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications' -Name 'ToastEnabled' -Value 1
sc.exe stop  WpnUserService_13dbd4 ; sc.exe stop WpnService
sc.exe start WpnService             ; sc.exe start WpnUserService_13dbd4   # 后者不会自动回来，必须手动起
```

## 验证记录

- [x] 策略值已删除：`NoToastApplicationNotification` 不存在，键内仅剩 `NoTileApplicationNotification=1`
- [x] `ToastEnabled = 1`；`NOC_GLOBAL_SETTING_TOASTS_ENABLED = 1`（上一轮改的，保留）
- [x] 服务恢复：`WpnService = Running`、`WpnUserService_13dbd4 = Running (PID 26936)`
      —— 中间被我 `sc stop` 后停住，已手动起回
- [x] 分界对照（同一段日志，以 15:43:40 为界）：**之前 3150 = 1 次，之后 3150 = 0 次**
- [x] 合成 toast 端到端：`CreateToastNotifier('Qoder-Notify-Test4').Show()` **未抛异常**，
      ETW 出现 `2416 收到 / 2418 提交`，无任何 3150
- [x] **Qoder 修复后自己发出的 toast 真的送达了**（2026-11-06 16:38 复测 ETW，不再依赖用户目视）：
      窗口 15:40→16:38 共 539 条事件，`com.qoder.app` 相关 8 条 = 两次通知各 4 条：
      `15:49:39` 与 `16:08:54` 都是 `2416 收到 → 2418 提交 → 3052 → **3153 delivered to com.qoder.app**`，
      窗口内 **3150（被策略丢弃）= 0 次**。用户同时目视确认"现在已经可以弹提示了"。
      取证件：`02_证据日志\通知修复后端到端复测.txt`、`03_工具脚本echeck_qoder_toasts.ps1`
- [x] Qoder 独立开关与提示音：本机 `notification.turnMode = always`、`permissionRequestsEnabled = true`（改前留档在 `通知策略-改前留档.json`）；
      应用目录内没有独立的"提示音"设置项，声音由 toast 携带，端到端已响
- [!] **新发现的细节**：`WpnUserService_` 的后缀在两次测量之间从 `13dbd4` 变成了 `16fb81`
      （同一台机、同一用户）。⇒ **这个服务名不能写死**，要用 `Get-Service -Name 'WpnUserService_*'` 通配

## 可复用规则

1. **判"通知没弹"直接读 ETW，不要停在注册表**：
   `Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PushNotification-Platform/Operational'}`，
   看 `Id=3150` 的 `AppId` 与 `PolicyReason`。`GlobalSettingDisabled` = 策略/总开关层拦；
   没有 3150 但有 2416/2418 = 平台已收下，问题在显示端。
2. **三层开关按优先级排查**：`Policies\...\PushNotifications`（组策略，普通用户只读，需提权）→
   `PushNotifications\ToastEnabled` → `Notifications\Settings\NOC_GLOBAL_SETTING_TOASTS_ENABLED`。
3. **`WpnUserService_<hash>` 是按需启动**：手动 `sc stop` 之后不会自己回来，
   必须显式 `sc start`，否则 `CreateToastNotifier` 抛「通知平台不可用」——这是自造故障，别当成新线索。
4. **改开关前先确认它是不是被策略压住**，否则会出现"值改了、回读对了、行为没变"的假修复。
5. 顺带：`QuietHours\FullScreenProcess = PixPin.exe` 这类规则会在特定进程全屏时抑制 toast，是下一个可能的干扰源。

## 适用范围与不适用范围

- 适用：任何依赖 Windows toast 的桌面应用（Electron/Tauri/PWA）报"通知不响/不弹"
- 不适用：应用自绘浮层提醒（不走 Wpn 管道）；服务账号/远程会话（本就无交互桌面）

## 剩余风险

- ~~端到端仍未由用户确认~~（2026-11-06 16:38 已闭环：ETW `3153 delivered` ×2 + 用户目视确认）。
  **仍存的风险**是那条"谁在 2026-07-22 写入这批策略"未查清 —— 若某个优化工具周期性重写，
  `NoToastApplicationNotification` 会被再写回 1，而**表现完全一样**（应用侧毫无报错）。
  复测命令只要一行：看 `Microsoft-Windows-PushNotification-Platform/Operational` 里有没有 `Id=3150`。
- 删除策略会让**全部应用**的通知恢复（本机 17 个应用子键），属已知副作用；
  `NoTileApplicationNotification` 我特意保留未动。
- 这批策略是谁在 2026-07-22 写入的**未验证**，若某个优化工具会周期性重写，本修复可能被再次覆盖。

## 关联

- 相关记录：auto-memory 的 `feedback-no-unverified-cause-claims`（本条正是"第一版根因判错"的自我更正）、
  auto-memory 的 `reference-qoder-app-internals`（main.log 位置）——这两条在 `C:\Users\Admin\.qoder\memory\`，不在本库，不能用 wikilink；
  [[踩坑-无权限读ProgramData被当成文件不存在致误删服务拆掉内核]]（同类：权限伪装成状态）
- 相关分类：03-通用/03-调试与验证
- 本机产物：`02_证据日志\通知策略-改前留档.json`、`Windows通知总开关-改前留档.json`、
  `03_工具脚本\{probe_windows_notifications,probe_toast_delivery,remove_notification_policy,wpn_start_and_verify,check_qoder_toasts}.py|ps1`
