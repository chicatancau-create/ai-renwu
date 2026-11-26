# 规则：用 Viap 清理数据前，必检 D 盘联接效果与 Viap 更新

- 状态：`verified`（用户 2026-11-24 明确规定的长期默认规则，当日执行并验证）
- 触发：任何会话打算用 Viap（或同类 junction 迁移/清理工具）清理数据、内存、幽灵链接、强力卸载时。
- 背景：本机 C 盘 54 个目录已联接迁到 D 盘（`D:\DevCache` 及 `AppData-Local|AppData-Roaming`），D 侧是**真源**。用户担心清理工具把 D 盘真源当重复数据误删、或迁移效果已失效却继续清理。

## 动手前两项必检（缺一不可）

1. **D 盘效果还在不在**：
   - 首选体检脚本：`D:\PyCharm\Python\python.exe -X utf8 D:\AI-Tool-State\disk-audit\health_check.py`
     （核对 54 个登记联接目标、5 个关键目录探针写入必须落 D、三个基目录顶层幽灵联接扫描、home/AppData 双守护；全绿退出 0）。
   - 或分别跑 `D:\DSH-Guard\migrate_guard.py --quiet`、`D:\DSH-Guard\migrate_guard_appdata.py --quiet`，退出码须 0。
   - 发现回流/失效/幽灵：先修复（守护会自动合并回 D），再谈清理。
2. **Viap 是否需要更新（结合本机）**：
   - 本机包 `H:\下载\Viap`（v1.3.3）对比 `https://github.com/Chunyu33/viap/releases/latest` 的 `tag_name`；
   - 有新版先核官方 SHA256 digest 再换包；确认本机安装状态（2026-11-24 为未安装）；
   - 若已安装，先确认其迁移历史已用「扫描目录联接重建历史」导入本机 54 个联接。

## 红线

- `D:\DevCache*` 永远不是「重复数据/可清理内存」，任何清理功能不得指向它。
- 幽灵清理只清**目标缺失**的失效联接；本机健康联接扫描结果应为 0，报出条目先人工核对。
- 不对已是联接的目录重复迁移。

## 验证记录

2026-11-24 17:27 体检：54 联接异常 0、探针 5/5 OK（npm/Code/Tencent/Doubao/.dsh）、幽灵 0、守护 home 26 + local 15 + roaming 13 全正常退出 0；应用无崩溃事件；Viap 官方最新仍 v1.3.3（无需更新）、本机未安装。

## 关联

- [[经验-AppData缓存迁D盘复用DSH-Guard核心按组包装]]
- 任务区：`G:\AIrenwu\04_磁盘与系统\磁盘整理\Viap-完全使用手册.md` 第〇节（同规则）、第八节（本机联接对照）
- 任务区：`G:\AIrenwu\04_磁盘与系统\磁盘整理\迁移防回归守护说明.md`
