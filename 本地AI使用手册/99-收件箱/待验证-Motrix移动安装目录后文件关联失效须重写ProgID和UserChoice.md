---
title: "Motrix 移动安装目录后文件关联失效：重写 HKCU ProgID 的 open\command"
date: 2026-11-15
domain: common
category: 99-收件箱
status: needs-review
severity: low
stack: [Windows 11, 注册表, Motrix, Electron]
tags: [文件关联, ProgID, UserChoice, 元数据为2026-11-15补登]
---

# 待验证：Motrix 移动安装目录后文件关联失效（ProgID 内核已证实，UserChoice 断言被本机推翻）

> **元数据为 2026-11-15 体检时补登**（原记录无 frontmatter）。`status` 定为 `needs-review`
> 而非 `verified`，依据见文末「2026-11-15 只读复核」——原文两条断言与本机现状相反，
> 且脚本里有不可执行的占位符。没有端到端复现过「双击 .torrent 真的用 Motrix 打开」，
> 所以不替它签「已验证」。

## 2026-11-15 只读复核（实测，未做任何写入）

只读探测本机注册表与安装目录，结果**部分推翻原文**：

| 原文断言 | 本机实测 | 判读 |
| --- | --- | --- |
| 步骤 1 要设 `HKCU\SOFTWARE\Classes\.torrent` 默认值为 `Motrix.torrent` | 键存在，但 **`(Default)` 为空** | 该步未生效或被回滚 |
| 步骤 2/3 写 ProgID 与 magnet 的 `open\command` | 两处均存在，值指向 `D:\_整理\01-软件\04-网络与下载\Motrix\Motrix.exe "%1"` | 搬盘后确实改过，与「移动目录后失效」的场景吻合 |
| **步骤 4「`FileExts\.torrent\UserChoice` 必须写，否则系统默认应用不生效」** | 该键 **不存在** | **与本机现状相反**：没有它，关联命令照样是好的。原文这条站不住 |
| `UrlAssociations\magnet\UserChoice` | 存在，`ProgId=Motrix.torrent` | 存在，但 magnet 指向一个 torrent 型 ProgID，是否有意未知 |

原文脚本里两条 `Set-ItemProperty "...\UserChoice"` 用了字面 `...` 占位符，**照抄必然报错**；
下方「修复方法」已把占位符补成完整键路径，但**补的是路径，不是验证**——真正待确认的是
Windows 11 对 `UserChoice` 有哈希与所有者 ACL 保护、直写通常会被系统回滚，原文没提这一点。

**待复现才能升级成 `verified` 的最小动作**：拿一个 `.torrent` 文件双击，看是否落到 Motrix；
再决定 `UserChoice` 到底该由系统「默认应用」设置页写、还是直写注册表可行。二者未实测，勿当结论。

## 现象
Motrix 从 C 盘移动到 D 盘后，设置→集成页面显示：
- .torrent 文件：无法确认
- 磁力链接：无法确认

## 根因
Electron 应用（如 Motrix）的文件关联写在注册表两个地方，移动安装目录后全部失效：
1. `HKCU\SOFTWARE\Classes\` 下的 ProgID 和扩展名关联
2. Windows 11 的 `UserChoice` 默认应用设置（**注：这条受系统保护，直写常被回滚，见上方复核**）

## 修复方法
```powershell
$motrixExe = "D:\_整理\01-软件\04-网络与下载\Motrix\Motrix.exe"   # 本机实测路径；换机器要改

# 1. 注册 .torrent 扩展名
New-Item -Path "HKCU:\SOFTWARE\Classes\.torrent" -Force
Set-ItemProperty "HKCU:\SOFTWARE\Classes\.torrent" -Name "(Default)" -Value "Motrix.torrent"

# 2. 注册 ProgID
New-Item -Path "HKCU:\SOFTWARE\Classes\Motrix.torrent\shell\open\command" -Force
Set-ItemProperty "HKCU:\SOFTWARE\Classes\Motrix.torrent\shell\open\command" -Name "(Default)" -Value "`"$motrixExe`" `"%1`""

# 3. 注册 magnet 协议
New-Item -Path "HKCU:\SOFTWARE\Classes\magnet\shell\open\command" -Force
Set-ItemProperty "HKCU:\SOFTWARE\Classes\magnet\shell\open\command" -Name "(Default)" -Value "`"$motrixExe`" `"%1`""

# 4. Windows 11 UserChoice —— 原文称「必须写」，但本机 .torrent\UserChoice 缺失而关联正常，
#    且该键受哈希+ACL 保护，直写未必生效。先试系统「设置 → 应用 → 默认应用」，别硬写注册表。
$uc1 = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.torrent\UserChoice"
$uc2 = "HKCU:\SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\magnet\UserChoice"
New-Item -Path $uc1 -Force
Set-ItemProperty $uc1 -Name "ProgId" -Value "Motrix.torrent"
New-Item -Path $uc2 -Force
Set-ItemProperty $uc2 -Name "ProgId" -Value "Motrix.torrent"
```

## 额外注意
- 同时要更新桌面和开始菜单快捷方式的 TargetPath
- 任务栏固定的旧快捷方式要删掉重新固定
- Motrix 2.x 的 RPC 端口默认 16800，密钥在 settings.json 的 engine.rpcSecret 里
