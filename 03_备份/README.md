# 03_备份 · 备份清单

> 本目录是各类**原件/配置/数据库备份**，共 6 套。备份内部内容**不改写、不搬运**。
> 命名惯例：`<对象>-原件备份-<日期>`；一次性废弃脚本归 `_已废弃脚本归档_<日期>`。

## 🔴 最高危警告（递归删除前必看）
- **`archived-cleanup-20261115\node_modules` 是一个 Junction，指向活体 `D:\DevCache\.dsh\profiles\desktop\node_modules`。**
  对本备份目录做「递归删除/清空」会**穿透 Junction 删掉正在使用的 DSH profile 依赖**。
  如需清理该备份，必须先单独移除 Junction（`rmdir` 只删链接不删目标），绝不能 `Remove-Item -Recurse` 整目录。

## ⚠ 禁跑
- **`_已废弃脚本归档_20261115`** 内脚本含硬编码删除路径，曾致 WorkBuddy 79% 会话零字节事故。**不要再运行其中任何脚本。**
  详见其 `README_为什么归档.md`。活体替代：`D:\DSH-Guard\migrate_dir.py` + `migrate_guard.py`（计划任务 DoubaoMigrateGuard）。

## 备份清单

| 备份套 | 内容 | 用途 / 回滚 |
|---|---|---|
| _backup | cc-switch 数据库快照 cc-switch-db-20261115-004737.db（13.2MB）+ headroom-wire\claude/codex 配置快照 + router-recovery\router-before-022606.py + script-pathfix\20261115-020344 三脚本 | 2026-11-15 环境修复期的配置/数据库恢复点 |
| _已废弃脚本归档_20261115 | 41 个一次性 C 盘缓存迁移脚本（migrate/cleanup/revert/move 等）+ _脚本源码.zip | **禁跑**；见 README_为什么归档.md |
| archived-cleanup-20261115 | 清理归档 7 文件 + 🔴 node_modules Junction（指向活体 DSH profile） | 清理留档；删除须先拆 Junction |
| DeskBox-原件备份-20261003 | 57 件：15 分类快捷方式 .lnk + 重建清单.md + 待确认-5项.md | DeskBox 快捷方式重建基线 |
| DeskBox-原件备份-20261106 | VPN\fix-network.v2.0.bat | DeskBox 网络修复脚本原件 |
| 本地AI使用手册-原件备份-20261115 | 回滚说明.txt + 6 文件快照 | 改手册前快照；回滚说明已注明 #RRGGBB 改名不建议回滚（Obsidian 死链）、Motrix 记录降级收件箱 |

## 备注
- 手册现用实体在 `G:\AIrenwu\本地AI使用手册`（2026-11-16 从 E 盘迁入）；本目录的手册备份是**迁入前**的旧快照，仅作回滚参考，不是活体。
- 备份体积大头是 cc-switch 数据库（13.2MB）；其余多为文本/快捷方式。
