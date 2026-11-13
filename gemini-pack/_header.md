# 双仓数据包：CodeWeave × 全栈工程师学习资料库

> 供 Gemini 做「双仓数据契约 / 内容联动」架构分析的真实代码快照
> 生成：2026-11-12 · 方式：本机只读扫描（两个并行扫描员 + lead 交叉验收）· 未修改任何源仓库
> 本文件 = 分析请求与交叉核对结论（§0） + CodeWeave 快照全文（§A） + 资料库快照全文（§B）

## 0. 这份数据包是什么 / 请你（Gemini）做什么

背景：你此前无法爬取 GitCode 上的两个公开仓库（平台反爬拦截），只能基于仓库名给出「CodeWeave（软件引擎）+ fullstack-study-library（资料库）」的双仓解耦建议：数据契约 manifest.json、规范化 YAML frontmatter、Colocation 目录、三种同步方案（submodule / 构建期静态 JSON / 平台 OpenAPI）、weave 双向锚点。用户本地有这两个仓库，本数据包按你的要求抓取了 README、核心配置、目录结构，并额外做了**内容消费管线的代码级核查与两仓交叉核对**。

请你基于以下真实材料修订/深化之前的架构建议，重点回答 §0.3 的问题清单。

材料结构与证据分级：
- §A = CodeWeave 快照（8 节：概览/目录树/规则文档/README/核心配置/技术栈/内容消费现状/主入口），全部磁盘原文 + file:line 证据。
- §B = 资料库快照（9 节 + 2 附录：概览/目录树/统计/根文档/frontmatter/链接风格/scripts 与 CI/同地性/gitignore/交接文档/未确认清单）。
- 标注约定：「实测」= 扫描员或 lead 直接对磁盘/代码核验；「宣称」= 仓库内文档原文（已嵌入），未独立验证；「未确认」= 判不了，不下否定结论。

## 0.1 两仓身份（实测）

| | CodeWeave（主软件） | 全栈工程师学习资料库（资料库） |
|---|---|---|
| 本地路径 | `G:\CodeWeave` | `E:\OBsidian\全栈工程师学习资料库` |
| 远端 | github.com/chicatancau-create/CodeWeave · gitcode.com/zhoumoyukuai/CodeWeave | github.com/chicatancau-create/fullstack-study-library · gitcode.com/zhoumoyukuai/fullstack-study-library · atomgit.com/zhoumoyukuai/fullstack-study-library |
| 分支 @ HEAD | codex/project-layout-20261106 @ 396d3fa（2026-11-12） | chore/fullstack-upgrade @ d84e132（2026-11-11） |
| 形态 | 三端工作区：网页端（React 19.2.8 + TS 5.9.3 + Vite 8.2.1 Rolldown + 零依赖纯 Node 服务）/ 应用端（C++23 Win32 壳 + 可选 Qt 6.8.3 QML，CMake+MSVC）/ 移动端（Kotlin 2.0.21 + Compose Material3，C++20 mobile-core） | Obsidian 库：14 个顶层目录；自有 md 734 篇、代码 557 个；另有 05-外部资料库镜像 md 137,953 篇 / 13GB（gitignored，不进 Git） |
| 根 README | 无（规则在 AGENTS.md + 工程文件/项目结构索引.md，全文见 §A3） | 有（4.7KB，全文见 §B4.1） |
| Git 跟踪规模 | 见 §A1 | 1,938 文件 / 736 md（工作区现状口径） |

## 0.2 七个关键事实（lead 交叉核对，按对架构决策的影响排序）

### ① CodeWeave 不是白纸——网页端已内置一套 manifest 数据契约（实测，代码为证）

- 读库根相对路径 `CodeWeave/content-manifest.json`（`网页端/项目/server/service/server/content/index.mjs:14`），强校验 `schemaVersion===1`（:48）+ 稳定 `vaultId`（:51）。
- 代码实际消费的字段：`schemaVersion` / `vaultId` / `publishWhitelist`（含 topicIndexPath、topicIdMapPath）/ `sourceRegistry`（verificationStatus）/ `topics` / `publishedContentIds`。**无独立 JSON Schema 文件**，契约散在 compiler.mjs / index.mjs / validation-codes.yaml；字段表全文见 §A7.2。
- frontmatter 只支持**受限子集**：顶层 `key: value` 标量 + 行内 `[a,b]` 列表（markdown.mjs:99 parseRestrictedFrontmatter）。你建议的多行嵌套 YAML（如 `stack:` 换行列表）**不被支持**，需写成行内形式。
- 管线：vault → manifest → 编译快照（compiler.mjs:825 compileContent，maxTopicBytes=200_000）→ 同源 API → 受限 Markdown 渲染；另有证据写回通道（预览→确认→提交备份→可回滚，§A7.6）。
- 注意：§A7.3 称该子集「与资料库 Python 工具（check_vault.py / build_topic_index.py）同语义」，但这两个工具在当前资料库工作区**不存在**（见②），可能属于旧布局/历史版本，未确认。
- **含义：资料库应产出与这套现有契约兼容的清单，而不是新造 weave-index.json。**

### ② 两仓当前事实上失联——CodeWeave 硬编码的库布局在资料库里全部不存在（实测，最重要的发现）

- CodeWeave 两端硬编码的库根相对路径（§A7.5）：`CodeWeave/content-manifest.json`、`CodeWeave/同步报告/同步记录.json`、`全栈工程师学习计划/进度追踪.md`、`全栈工程师学习计划/全栈竞赛长期冲刺总计划.md`、`knowledge/vault/CodeWeave/rules/teaching-rules.json`、`tools/check_vault.py`、`tools/build_topic_index.py`。
- lead 定点存在性检查：以上路径在资料库工作区**全部 MISSING**；`git ls-files` 当前分支索引也**全部为空**（历史提交未查）。输出原文见 §0.5.1/§0.5.2。
- 资料库 `000-学习总览.md` 原文（§B4.2）：本库 2026-11-05 起由原名「全栈工程师学习计划」改名重组为现在的「01-阶段课程…09-整合任务」布局；旧名仅存于 `90-历史归档/全栈工程师学习计划-recover/`（48 篇 md，2026-11-04 快照）。
- `E:\OBsidian` 下不存在独立的「全栈工程师学习计划」vault（实测，§0.5.3）。**注意 `E:\OBsidian\.obsidian` 存在于父级**，资料库自身无 .obsidian——真实 Obsidian vault 根可能是 `E:\OBsidian` 这一层，CodeWeave 绑定路径需按此核对（未与用户确认）。
- CodeWeave 本机两端均未配置真实库根（server/config 只有 example、server/data 不存在、Qt 库根在 QSettings，§A7.9）。
- **含义：方案第一步不是「设计新契约」，而是「修复现有契约的路径失配」——要么资料库补出 CodeWeave 期望的布局与清单，要么改 CodeWeave 两端硬编码路径适配新布局。两条路线的取舍请你分析（§0.3 问题 2）。**

### ③ 自有学习笔记 frontmatter 覆盖率 ≈ 0%（实测抽样 + 全量统计）

- 全库 55.0%（76,285/138,687）有 fm，但几乎全部来自 05 外部抓取镜像（76,268 篇）；自有目录 01/02/06/07 全 0；08 的 17 篇有 fm 者全部是 RAG-GoldenSet 考题语料数据（字段 id/tenant/title/version），不是笔记元数据（§B5）。
- 你建议的 `stack` / `sandbox_path` / `related_ids` 字段**全库 0 命中**。
- **含义：frontmatter 规范化是纯增量工作，且必须落在 CodeWeave 受限子集能解析的形式内（见①）。**

### ④ 无知识索引；已有 manifest 是「证据清单」不是「知识索引」（实测）

- 无 `scripts/build-index.js`、无 `weave-index.json`。scripts/ 仅 3 个文件：check_student_packages.mjs / verify_all.mjs / verify_archive.sh（§B7.1）。
- 自有 `evidence/manifest.json` 共 29 份（01:9 / 06:14 / 08:6，与总览 §1.5 宣称逐目录吻合），内容是命令退出码 + 文件 sha256 的**实验证据清单**，与你建议的知识点索引 manifest.json 用途不同，不可混用（§B3.2/3.4）。
- README 宣称「17 份 manifest 校验通过」对账：仓内 14（E01–E13+G1）实测存在 + 外部 3（P02/P03/P04）在 `E:\fullstack-code`（未扫描，未确认）；「校验通过」为宣称，本次未复跑（§B3.3）。

### ⑤ 05 外部镜像必须分层排除（实测统计）

- 05-外部资料库：md 137,953/138,687（99.5%）、代码 85,388、体积 13GB；题库/知识库被 .gitignore 整体排除（本地镜像不进 Git，用 材料清单.md 复现，§B9）。
- **含义：任何全局索引 / manifest 生成与 CodeWeave 拉取方案都必须先排除或单独分层 05，否则被拖垮。**

### ⑥ Colocation 已部分实现；项目代码跨仓分离（实测）

- 06-实验代码：每实验单元自包含 README+src/tests/scripts/evidence（已符合你建议的 Bundle 精神）；01 教学单元同构（§B8.1）。
- 07-项目实现：已清空为纯索引 README，P02/P03/P04 真实源码在外部私有仓 `E:\fullstack-code`（仅验存在性，内容未扫描）；07 README 路径表用 `projects/` 前缀而 verify_archive.sh 用根级前缀，口径分歧未确认（§B8.2/附录B）。
- **含义：缺口是知识点级 fm + 跨单元 related_ids + 全局索引，不是推倒重来目录结构。**

### ⑦ CI 名存实亡——「GitCode CI 自动生成 manifest」方案需现实校正（文档宣称，未查 API）

- 12 个根 workflow 全部从未在 Actions 实跑；2026-11-08 起计费阻断（README/交接文档宣称，原文已嵌入 §B7.2/附录A）。
- 「全绿」仅指本机门禁，本次未复跑（只读纪律）。
- **含义：你的方案 2（构建期拉取 + 静态 JSON API）若依赖 CI，需先解决计费/runner 问题，或改为本机脚本生成 + 提交。**

## 0.3 请你（Gemini）回答的问题清单

1. **契约路线**：基于 §A7.2 的现有字段契约，资料库侧 manifest 生成器应如何设计（输入 = 01/06/08 自有内容，输出 = 与 `CodeWeave/content-manifest.json` 兼容的格式）？给出字段映射表 + 受限 frontmatter 子集内的 fm 模板（行内列表形式）。
2. **路径失配修复**：②的两条路线（资料库补旧布局 vs 改 CodeWeave 硬编码）各自的改动面、风险、工作量对比；推荐哪条？若改 CodeWeave，列出需同步修改的文件清单（§A7.5 已给路径与行号）。
3. **同步方案选型**：结合 ⑦CI 不可用、⑤13GB 镜像、应用端课程走构建期导出只读包（§A7.7，Qt 运行期不读 manifest）、移动端无内容加载逻辑（§A7.9）的现实，你原来的三方案哪个可行？给出修订版与理由。
4. **分层索引**：如何把 05 外部镜像排除在知识索引外、又保留「按需检索」能力？材料清单.md 复现机制是否够用？
5. **跨仓项目**：07 → E:\fullstack-code 的分离如何用 sandbox_path 类字段机器可读化？projects/ 前缀口径分歧如何统一？
6. **知识图谱**：自有笔记 wikilink（961）与 markdown 链接（1034）混用、无 fm id 可依赖（§B6），related_ids / 知识图谱锚点 / 你建议的 `// @weave-step-N` 代码双向锚点如何落地？
7. **写回通道**：CodeWeave 已有证据写回（§A7.6，网页预览→确认→备份→回滚；Qt 8MB 上限+锁），资料库侧需要什么约定才能安全接收？

## 0.4 边界与隐私（本数据包不包含什么）

- 未包含：CodeWeave `工作区/`（隐私）、`.local/`、`.claude/` 内容；资料库 `.workbuddy/` 内容、05 外部镜像正文（13GB，只统计与结构）；`E:\fullstack-code` 内容（外部私有仓，仅存在性探测）。
- 脱敏：两仓 git 远端 URL 均无内嵌凭据（实测）；两份报告密钥/PII 扫描 0 命中；签名私钥类文件（*.pfx）只记录存在。
- 未确认清单：§B附录B 8 条（外部仓内容 / CI 历史 / 门禁数字均未复跑）；§A7.9（本机库根未配置等）。lead 补充：旧布局路径是否存在于资料库历史提交未查；E:\OBsidian 父级 .obsidian 对 vault 根判定的影响未与用户确认；资料库 .gitignore 注释提及 tools/catalog_tool.py 但工作区无 tools/ 目录（口径差异，未确认）。
- 统计口径：资料库按工作区现状统计，未做工作区 vs HEAD 差异比对（交接文档警告存在其他会话未提交改动）。

## 0.5 lead 验收记录（抽查证据）

- §A 报告抽查：MANIFEST_PATH 常量、schemaVersion 校验、react/vite/ts 版本号均与源文件行号吻合（content/index.mjs:14/:48、网页端/项目/package.json:30/44/46）。
- §B 报告抽查：frontmatter 抽样（01-阶段课程/README.md 等 3 份首行即正文）、scripts/ 3 文件清单、库根 14 目录、recover 归档结构均与磁盘吻合；29 份 evidence manifest 分布与总览 §1.5 逐目录吻合。
- ②的存在性检查、git ls-files 核查、父级目录检查输出原文如下（脚本存于 gemini-pack/_lead_*.py，可复跑）。

### 0.5.1 实测输出：CodeWeave 硬编码路径在资料库的存在性（_lead_verify.py）

```text
MISSING CodeWeave
MISSING CodeWeave/content-manifest.json
MISSING CodeWeave/同步报告/同步记录.json
MISSING tools
MISSING tools/check_vault.py
MISSING tools/build_topic_index.py
MISSING knowledge
MISSING knowledge/vault
MISSING 全栈工程师学习计划
MISSING 全栈工程师学习计划/进度追踪.md
MISSING teaching-rules.json
MISSING manifest.json
MISSING weave-index.json
MISSING build-index.js
EXISTS  scripts
EXISTS  05-外部资料库/材料清单.md
```

### 0.5.2 实测输出：git ls-files 当前分支索引（_lead_git_check.py，8 个 pathspec 全部为空）

```text
=== git ls-files -- CodeWeave/* ===          （空）
=== git ls-files -- tools/* ===              （空）
=== git ls-files -- knowledge/* ===          （空）
=== git ls-files -- 全栈工程师学习计划/* ===  （空）
=== git ls-files -- *content-manifest* ===   （空）
=== git ls-files -- *check_vault* ===        （空）
=== git ls-files -- *teaching-rules* ===     （空）
=== git ls-files -- *build_topic_index* ===  （空）
```

### 0.5.3 实测输出：E:\OBsidian 一级（_lead_sibling.py）

```text
DIR  .obsidian
DIR  全栈工程师学习资料库
DIR  高性价比人生指南
（E:\OBsidian\全栈工程师学习计划 MISSING —— 旧库名不存在独立 vault）
```
