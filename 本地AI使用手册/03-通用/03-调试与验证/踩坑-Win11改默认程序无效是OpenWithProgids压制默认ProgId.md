---
title: "Win11 双击还是弹「打开方式」：只要扩展名下存在 OpenWithProgids，系统就无视默认 ProgId；唯一有效的是覆盖 UserChoice 指向的那个 ProgId"
date: 2026-11-15
domain: common
category: 调试与验证
status: verified
severity: high
stack: [Windows 11, 文件关联, 注册表, UserChoice, OpenWithProgids]
tags: [双击默认程序, OpenWithProgids, UserChoice, AssocQueryString, 免提权, 哈希保护]
---

# 问题：把 `HKCU\Software\Classes\.zip` 默认值改成自己的 ProgId，双击还是弹「打开方式」

## 一句话结论

Windows 11 里，**扩展名键下只要存在 `OpenWithProgids` 子键，系统就不再采用该扩展名的默认 ProgId**，
直接退化成 `C:\WINDOWS\system32\OpenWith.exe "%1"`（未缓存查询返回 `HRESULT 0x80070483` = `ERROR_NO_ASSOCIATION`）。
真正有决定权的只有每用户的 `UserChoice`（哈希受保护，伪造不了）。
**免提权的正解：读出 `UserChoice` 指向哪个 ProgId，然后只在 HKCU 覆盖那个 ProgId 的 `shell\open\command`。**

## 触发条件与影响

- 触发条件：想用一个自建 ProgId（例如「解压并打开文件夹」）接管某个**已有打开方式**的扩展名。
- 影响：改默认值「看起来完全正确」（`reg query` 回读无误），双击行为却纹丝不动；很容易误判成「注册表没生效/需要重启」，
  甚至误判成 PowerShell 是 32 位被重定向（本机实测 `Is64BitProcess: True`，排除）。
- 更坑的是：**不同扩展名表现不一样**——有的回退到 OpenWithList 的 MRU，有的直接 NO_ASSOCIATION，看着像两件事。

## 决定性对照实验（这才是判据）

自建临时扩展名做单变量测试，不要拿真实扩展名猜：

| 临时扩展名 | 设置 | 解析结果（`AssocQueryStringW`，即资源管理器自己用的函数） |
|---|---|---|
| `.dshtestF` | 默认值=`DSH.UnzipAndOpen` + **有** `OpenWithProgids` | ❌ `OpenWith.exe "%1"` |
| `.dshtestF` | **只删掉** `OpenWithProgids`，其余不动 | ✅ 立刻解析到我们的命令 |
| `.dshtest6/7/8` | 只加 `Content Type` / `PerceivedType` / `PersistentHandler` | ✅ 均正常 |
| `.dshtest9/B/C` | 加 `OpenWithProgids` | ❌ 全部失败 |

→ 单变量排除其余三项，**锁定 `OpenWithProgids`**。

```powershell
# AssocQueryStringW：ASSOCSTR_COMMAND=1；ASSOCF_NONE=0；ASSOCF_IGNOREUNKNOWN=0x400
# 关键：不带 cache（0x400）也要一起测，能证明不是缓存
```

## 根因分析

- 「默认 ProgId」写在 `HKCR\.<ext>` 的默认值里，它只是**候选**，不是决定。
- 存在 `OpenWithProgids` 意味着「这个扩展名有多个可选打开方式」→ 系统认为尚未确定用户意图 → 交回给「打开方式」流程。
- 只有 `HKCU\...\FileExts\.<ext>\UserChoice`（带 `Hash` 校验）才是用户的真实选择；该子键的 ACL 还常带
  `Deny <user> SetValue`，连删除都要先接管所有权。
- 真实扩展名的 `OpenWithProgids` 通常在 **HKLM**，非管理员删不掉 → 所以「改默认值」这条路线对真实扩展名**永远无效**。

## 最小修复（免提权）

```powershell
$ext = '.rar'
$uc = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\$ext\UserChoice"
$progId = $uc.ProgId          # 例：WinRAR / WinRAR.ZIP / Applications\WinRAR.exe
# 只覆盖这个 ProgId 的命令（ProgId 里可能有反斜杠，注意建多级键）
Set-ItemProperty "HKCU:\Software\Classes\$progId\shell\open\command" -Name '(default)' `
  -Value 'wscript.exe //nologo //B "C:\path\helper.vbs" "%1"'
```

本机三条实际落点：

| 扩展名 | `UserChoice` 的 ProgId | 覆盖位置 |
|---|---|---|
| `.rar` | `WinRAR` | `HKCU\Software\Classes\WinRAR\shell\open\command` |
| `.zip` | `WinRAR.ZIP` | `HKCU\Software\Classes\WinRAR.ZIP\shell\open\command` |
| `.7z` | `Applications\WinRAR.exe` | `HKCU\Software\Classes\Applications\WinRAR.exe\shell\open\command` |

> **必须满足的前提**：已经存在一个**合法** `UserChoice` 指向该 ProgId。
> 本机走过的弯路：`.zip` 当时**没有** `UserChoice`，我直接改 `WinRAR.ZIP` 的命令 → `.zip` 反而变成「打开方式」。
> 结论：**没有 `UserChoice` 时改 ProgId 无效甚至有害。**
>
> **没有 `UserChoice` 的扩展名（本机 `.tar` / `.gz`）怎么免提权解决**：让用户「右键 → 打开方式 → 选那个程序 → 始终使用」一次，
> 生成 `UserChoice` 指向已被劫持的 ProgId，之后自动生效。这比提权删 HKLM 的 `OpenWithProgids` 安全得多。

## 验证记录

- `AssocQueryString` 对 `.rar` / `.zip` / `.7z`，**cached 与 `ASSOCF_IGNOREUNKNOWN`（nocache）两种查询都返回**我们的 wscript 命令，exe 解析为 `C:\WINDOWS\system32\wscript.exe`。
- `.tar` / `.gz` 未解决：无 `UserChoice` + HKLM 有 `OpenWithProgids` → 仍 `OpenWith.exe` / `0x80070483`（如实记录，未修）。
- 备份先行：`C:\Users\Admin\.dsh\tools\fileexts-backup.txt`（各扩展名 OpenWithList / MRUList 快照）、`fileexts-export\FileExts-7z.reg`。
- 未验证：真实双击（用户侧行为）。**不把 `AssocQueryString` 通过写成「双击已确认」。**

## 可复用规则

- **判「默认程序改不动」只看 `AssocQueryString`（cached + nocache 各一次），不看 `reg query` 回读。** 回读成功不等于生效。
- 排查顺序：`UserChoice` → 该 ProgId 的命令 → 扩展名键下有没有 `OpenWithProgids` → 缓存。倒着查会白花时间。
- **不要伪造 `UserChoice`**：`Hash` 是系统算的，改了会被判定无效并重置。
- **不要伪造「默认值」来抢已有关联**：要么走「打开方式」一次生成 `UserChoice`，要么提权动 HKLM。
- 做单变量实验时**用自建临时扩展名**，跑完删掉；在真实扩展名上试错会污染用户的「打开方式」历史。

## 适用范围与不适用范围

- 适用：Windows 10/11 桌面 `.lnk`/文件关联层面的「双击默认程序」。
- 不适用：UWP/Store 应用的协议激活；`HKLM` 被策略锁定（`NoFileAssoc`/组策略）的环境；通过 installer 写入的 `RegisteredApplications` 能力声明。

## 剩余风险

- 覆盖通用 ProgId（如 `WinRAR`）会连带改变**其它**指向同一 ProgId 的入口（文件管理器「解压到」菜单也可能被影响）。
- 程序自更新/重装可能重写 HKLM 侧命令或重建 ProgId，需要复查。
- `.rar` 早前被删掉的 `HKCU\...\FileExts\.7z` 键未还原，`FileExts-7z.reg` 可导回，影响仅是「打开方式」历史列表。

## 关联

- [[03-通用/03-调试与验证/踩坑-任务栏图标变白按AUMID查开始菜单快捷方式IconLocation|任务栏图标变白：按 AUMID 查开始菜单快捷方式的 IconLocation]]
- [[03-通用/03-调试与验证/踩坑-计划任务action裸命令名报0x80070002须写全路径|计划任务 action 裸命令名报 0x80070002：写全路径并回查 LastTaskResult]]
