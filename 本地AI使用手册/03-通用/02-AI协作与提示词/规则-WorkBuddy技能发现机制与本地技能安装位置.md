---
title: "本机技能发现机制：本地技能放哪、何时被识别、如何实现'默认调用'"
date: 2026-10-13
domain: common
category: 03-通用/02-AI协作与提示词
status: verified
severity: low
stack: [WorkBuddy, skills, Obsidian]
tags: [技能库, 技能发现, 默认调用, 长期记忆接入]
---

# 规则：往本机加一个技能，文件该放哪、多久生效、怎么才算"默认调用"

## 一句话结论

本机（WorkBuddy）的技能是**从目录自动发现**的：把 `SKILL.md` 放进
`C:\Users\Admin\.workbuddy-ai\skills\<目录名>\` 即可，**不需要注册表、不需要改配置**；
技能清单缓存会自动刷新（实测约十几分钟内），**无需重启客户端**。
`SKILL.md` 的 `description` 同时决定"能不能被自动调用"与"在列表里显示什么"。

## 触发条件与影响

- 项目或功能：给本机增加/迁移自定义技能，或想让某条长期规则被 AI **默认调用**。
- 环境与版本：Windows，WorkBuddy 桌面端；技能根 `C:\Users\Admin\.workbuddy-ai\skills\`。
- 触发条件：新建本地技能、排查"为什么技能没出现在列表里"、想实现"默认调用"。
- 影响范围：决定自定义技能能否生效、多久生效、以及是否能被模型自动触发。

## 复现步骤

1. 前置条件：确认技能根目录 `C:\Users\Admin\.workbuddy-ai\skills\` 存在。
2. 操作：新建目录 `<技能名>\`，写入 `SKILL.md`（frontmatter 至少含 `name` + `description`），
   可选 `scripts/`、`references/`、`assets/`。
3. 预期结果：技能出现在技能列表中，可被模型自动调用。
4. 实际结果：创建后**立即可被识别**——缓存于创建后约 16 分钟自动刷新，列表由 73 → 74 条，
   新技能 `disable=false`、`disableModelInvocation=false`。

## 证据

**技能根与结构**（与已注册的本地技能 `darwin-skill` / `vision-tool` 逐项对照，结构一致）：

```
C:\Users\Admin\.workbuddy-ai\
├── .skill-list-cache.json    ← 技能清单缓存（应用自动维护；在技能根的上一级，2026-11-13 实测更正）
└── skills\
    ├── <技能名>\
    │   ├── SKILL.md          ← 必需：frontmatter(name, description) + Markdown 正文
    │   └── scripts\          ← 可选：脚本、references、assets
    └── .disable_to_model_invocation_migration.json   ← 一次性迁移标记，非注册表
```

> 2026-11-13 实测更正：原结构图把 `.skill-list-cache.json` 画在 `skills\` 内；实际它在上一级 `.workbuddy-ai\`（`skills\.skill-list-cache.json` Test-Path 不存在、`.workbuddy-ai\.skill-list-cache.json` 存在）。文末「关联」节的路径一直是正确的，两处自相矛盾就此消除。

**缓存条目字段**（`.skill-list-cache.json` → `results[]`，实测 2026-10-13）：

```json
{
  "name": "local-ai-handbook",
  "filePath": "C:\\Users\\Admin\\.workbuddy-ai\\skills\\local-ai-handbook\\SKILL.md",
  "description": "本机 AI 工程知识库（E:\\本地AI使用手册）……",
  "source": "userSettings",
  "type": "prompt",
  "disable": false,
  "disableModelInvocation": false,
  "overrideKey": "local-ai-handbook",
  "version": "1.0.0",
  "iconSource": "local-ai-handbook"
}
```

**生效时间实测**：技能于 19:21 落盘 → 缓存 `savedAt` 19:37:24 刷新并收录（技能数 73 → 74）
→ `skill_management list` 已能列出该技能。**全程未重启客户端。**

**`_skillhub_meta.json` 是市场技能专用**：`darwin-skill`（市场安装）带它，内含 `skillId` / `pay_mode` /
`source: "marketplace"`；`vision-tool`（本地手写）不带它，也照常注册。
→ 本地技能**不需要、也不应伪造**该文件。

**显示名来源**：本地技能在列表里显示 frontmatter 的 `name`（如 `vision-tool`、`local-ai-handbook`）；
市场技能显示 `_skillhub_meta.json` 的 `name`（如 `darwin-skill` → "Skill 自主优化"）。
frontmatter 里的 `display_name` 对本地技能不生效。

## 根因分析

- 已确认的根因（机制）：技能根目录被应用监视，`SKILL.md` 被扫描进 `.skill-list-cache.json`，
  客户端按该缓存加载技能列表。`watch.dirs` 字段可看到被监视的目录集合。
- 排除过的假设：
  - 不是"需要注册表登记"——技能根下只有一个**一次性迁移标记** dotfile（`.disable_to_model_invocation_migration.json`）；清单缓存 `.skill-list-cache.json` 在上一级 `.workbuddy-ai\`（2026-11-13 实测更正，原文误记"两个 dotfile 都在技能根下"）。两者都不是注册表。
  - 不是"必须重启客户端"——实测缓存自动刷新即可生效。
- 问题归属：机制说明，非缺陷。

## 最小修复（操作要点）

1. **放对位置**：`C:\Users\Admin\.workbuddy-ai\skills\<目录名>\SKILL.md`。
   `name` 建议与目录名一致（列表用 `name`，`overrideKey` 也取 `name`）。
2. **写清 `description`**：它是"能否被自动调用"的**唯一触发依据**，要写全触发场景与关键词；
   中英双语可兼顾中文界面显示与英文关键词触发。
3. **实现"默认调用"**：让 `description` 覆盖目标任务类型即可；`disableModelInvocation` 保持 `false`
   （默认值）。若发现被置 `true`，说明该技能只能手动调用。
4. **想要中文显示名**：本地技能不支持；列表显示 `name`。若确需中文名，只能走市场安装（带 meta）。

## 验证记录

- [x] 结构对照：与 `darwin-skill` / `vision-tool` 逐项一致。
- [x] 自动发现：新技能被 `.skill-list-cache.json` 收录（73 → 74）。
- [x] 生效确认：`skill_management list` 能列出 `local-ai-handbook`，`disable=false`。
- [x] 未重启客户端即生效（实测）。
- [ ] 缓存刷新的确切触发条件（定时 / 文件变更 / 二者兼有）**未定位**，仅观测到约 16 分钟内自动刷新。

## 可复用规则

**要加一个本地技能 / 让某规则被默认调用时：**

1. 目录 `~\.workbuddy-ai\skills\<name>\` + `SKILL.md`（`name` + `description` 必填）→ 落盘即可。
2. **不要**动 `.skill-list-cache.json`（应用自动维护，手改有风险）；**不要**为本地技能造
   `_skillhub_meta.json`。
3. 想"默认调用"→ 把 `description` 的触发面写宽、写全关键词；`disableModelInvocation` 保持 false。
4. 落盘后等缓存刷新即可（实测十几分钟内）；期间不必重启客户端。

## 适用范围与不适用范围

- 适用：本机 WorkBuddy 的用户级技能（`C:\Users\Admin\.workbuddy-ai\skills\`）。
- 不适用：插件/连接器自带的技能（在 `plugins\...\skills\`，由插件管理）；
  项目级技能（`{workspace}\.workbuddy-ai\skills\`，作用域不同）；市场安装技能的元数据行为。

## 剩余风险

- 缓存刷新的**确切触发条件**未定位（只观测到约 16 分钟内生效）。若某次落盘后长时间不出现，
  优先怀疑：`SKILL.md` frontmatter 解析失败（YAML 语法错）、或目录名/`name` 冲突。
- **YAML 陷阱**：`description` 里含 Windows 路径的反斜杠时，必须用**单引号**包裹
  （双引号会把 `\本` 之类当转义序列处理）。本次即用单引号规避。

## 关联

- 相关记录：[[规则-技能库已收录逆向技能只放指针]]（技能实体放 `D:\Skills`，手册只放指针；
  本条补充"本机技能如何被发现"）
- 相关分类：[[03-通用/02-AI协作与提示词/README|AI 协作与提示词]]
- 相关代码、命令或文档：`C:\Users\Admin\.workbuddy-ai\.skill-list-cache.json`；
  `C:\Users\Admin\.workbuddy-ai\skills\local-ai-handbook\SKILL.md`
