---
title: 全机AI共享全局记忆存D盘Skills库并接线各Agent
date: 2026-11-19
domain: 03-通用
category: 02-AI协作与提示词
status: verified
severity: medium
stack: [Windows, DSH, Codex, Claude Code, OpenCode, OpenClaw, Continue, Qoder, MemSearch]
tags: [全局记忆, 共享记忆, 接线, 单向同步, no-clobber, 索引合并, orphan检查, 双远端备份]
---

# 全机 AI 共享全局记忆：实体存 D:\Skills\global-memory，接线走各 Agent 全局指令文件

## 一句话结论

用户要求「所有 AI 都要能用到它，这个记忆非常重要」（2026-11-19）：把 Qoder 国际版全局记忆单向导入 `D:\Skills\global-memory\`（125 条记忆 + MEMORY.md 索引），并入国内版独有 8 条与 8 个文件的带日期附录，再给本机每个有文件接线面的 Agent 追加「先扫共享记忆索引」的全局指令；实体随技能库自动双远端私有备份。**不注册成技能、不做 junction 实时共用。**

## 触发条件与影响

- 换 Agent / 换 Qoder 版本就「失忆」；`.qoder` 与 `.qoder-cn` 两套记忆完全独立（见关联规则），其余 Agent 根本没有这份记忆。
- 记忆里有用户画像、沟通硬约束、授权边界、大量本机踩坑判据——丢失或不同步会让每个 AI 重复踩坑、违反用户已定规矩。

## 做法（可复跑步骤）

1. **盘点 + 密钥扫描**：脚本量数文件数/字节数；按 `sk-` / `api_key` / `Bearer` / `AKIA` / `PRIVATE KEY` 形态扫全文，干净才允许进备份仓库。本次 118 个 .md / 595,063 字节，扫描干净。
2. **实体选址 `D:\Skills\global-memory\`**，理由：①记忆内先例「用户明确要求全机 AI 都能用 → 实体放 D:\Skills」；②随 `D:\Skills` 的 ops.py 自动双远端私有备份（GitHub chicatancau-create/ai-skills + GitCode zhoumoyukuai/ai-skills），记忆重要需持久；③D 盘比 E/F/G 可靠（同块无 DRAM NVMe 有 0x00 覆写史）；④密钥干净可推。
3. **单向导入脚本** `D:\Skills\global-memory\sync_from_qoder.py`：cp -n no-clobber（绝不覆盖本地）+ 逐文件 sha256 双端校验 + MEMORY.md 永不覆盖（合并索引）+ orphan 自动按 frontmatter description 补索引行 + provenance 说明幂等插入。本次拷 118、补源索引漏掉的 5 条、final_orphans=0。**源库只读不动。**
4. **接线面 = 各 Agent 全局指令文件**（不是技能目录）：

   | AI | 接线面 | 方式 |
   |---|---|---|
   | DSH | `D:\DevCache\.dsh\AGENTS.md`（`~/.dsh` junction 等价） | 追加「第〇节之二：全机共享全局记忆（强制触发）」，热重载即生效 |
   | Codex | `D:\DevCache\.codex\AGENTS.md` | 追加「二十一、全机共享全局记忆」 |
   | Claude Code | `D:\DevCache\.claude\CLAUDE.md` | 新建 |
   | OpenCode | `C:\Users\Admin\.config\opencode\AGENTS.md` | 新建 |
   | OpenClaw/FlowyAIPC | `C:\Users\Admin\.openclaw\workspace\AGENTS.md` | 在 `<!-- preset:end -->` 后追加 |
   | Continue | `C:\Users\Admin\.continue\config.yaml` | 尾部追加 `rules:` 块（单引号 YAML 防反斜杠转义；不动已有密钥行） |
   | Qoder 国内版 | `C:\Users\Admin\.qoder-cn\memory` | 单向 cp -n 补齐 + 索引手工合并 |
   | WorkBuddy / 豆包 | 无安全文件接线面（app 管理 memory） | 报告说明，需要时手动读共享库 |

5. **指针文本模式**（写进每个接线面）：动手前先扫 `D:\Skills\global-memory\MEMORY.md`（每条一行摘要，grep 定位）→ 读命中条目正文；涉及偏好/沟通/边界读 `user-role.md`；条目只是候选经验必须复核；只追加不改写；不写密钥；群聊不引用私人条目；刷新跑 sync_from_qoder.py。
6. **并集与冲突分诊**（同名 ≠ 同内容，必须逐文件 diff）：
   - 国内版 77 → cp -n 补 49 到 126 文件，0 覆盖；索引 = 国际版修正基底 + 国内独有行 + 快照说明；旧索引先备份；orphan=0、哈希 mismatch=0。
   - 8 条国内独有 → 拷入共享库 + 索引补行。
   - 30 个同名冲突三分类：23 个国际版更新 / 5 个同时间戳但国内版是子集 / 2 个国内版本地更新。共享库保留更丰富版本；国内旧副本按 no-clobber 不覆盖。
   - 「国内独有且共享库确实缺失」的实质内容（先用 marker grep 确认缺失，排除已被吸收/取代的）→ 程序化从 CN 原文抽取，以**带日期附录**逐字追加进共享库对应文件（本次 8 文件 +62 行），断言前缀字节未动。frontmatter/相关链接噪声不并入。
7. **语义检索**：`memsearch index D:\Skills\global-memory`（本地 ONNX bge-m3，无付费），`memsearch search <query> --source-prefix D:/Skills/global-memory` 验证命中。
8. **备份**：`wire_guard` 计划任务每 10 分钟自动提交推双远端（验收 = 远端 HEAD 与本地一致）；要立即备份就手动 `git add <具体文件>` + commit + `push origin main` + `push gitcode main`，再 `ls-remote` 核 HEAD。**ops.py 没有 backup 子命令**（只有 status/verify/start/stop/restart/wire/unwire/skills），别调 `ops.py backup`（会静默落到 status 显示，exit 0 但不提交）。

## 证据

归档：`G:\AIrenwu\01_任务归档\2026-11-19_导入Qoder全局记忆\`

- `02_证据日志\import_report.json` — 118 拷贝 + 全量 sha256 manifest，exit 0
- `02_证据日志\cn_sync_report.json` — intl=118 cn_before=77 cn_after=126 copied=49 conflicts=30 cn_unique=8 orphans=0 mismatch=0
- `02_证据日志\cn_unique_merge_report.json` — 8 条并入，shared_md=127，orphan=0
- `02_证据日志\cn_conflicts_analysis.json` / `cn_plus_only.txt` / `cn_unique_lines.txt` — 30 冲突逐文件分诊与独有行取证
- `02_证据日志\cn_addenda_report.json` — 8 文件附录追加（前后字节数、原文未动断言通过）
- `03_工具脚本\` — sync_to_qoder_cn.py / merge_cn_unique_to_shared.py / analyze_cn_conflicts.py / dump_cn_unique_lines.py / dump_plus_only.py / merge_cn_addenda.py
- 共享库协议与接线清单：`D:\Skills\global-memory\README.md`

## 根因分析（为什么这样接）

- **不做 junction 实时共用**：手册明令禁止——两个客户端同写 MEMORY.md 会互相覆盖（关联规则已实测）。
- **不注册成技能**：用户定规默认只开 skill-router + headroom，`D:\Skills-active` 是运维管的默认窗口禁改；且 Agent 会话开始就快照技能列表，改目录看不见。全局指令文件每次会话注入，才是「默认必用」的正确面（同 `规则-本地手册接入DSH成为默认前置` 的教训）。
- **no-clobber + 索引手工合并**：防旧索引覆盖本地新写；索引漏条目是复发缺陷（11-15 国际 5 国内 2），必须脚本复检 orphan。

## 验证记录

- 导入 exit 0，118 文件 sha256 双端一致，final_orphans=0。
- CN 同步 orphans=0、mismatch=0、unique_touched=0；共享库并集后 orphan=0。
- 8 个附录文件前缀字节断言通过（原文未动），新内容逐行在位。
- DSH `AGENTS.md` 追加后当场收到热重载 reminder，新节已注入会话（生效实证）。
- MemSearch 首轮 index 433 chunks（并集前）；并集+附录后增量重索引 44 chunks，exit 0；`memsearch search 'GitCode 凭据 private_token 查询串' --source-prefix D:/Skills/global-memory` 命中附录节本身（score 0.9919，heading「国内版补充（2026-11-19 并入）」）。双远端推送 HEAD 核对见归档报告。

## 可复用规则

- 全机共享记忆实体放 `D:\Skills\global-memory\`，接线走各 Agent 全局指令文件，指针文本统一「先扫索引→读正文→候选经验须复核」。
- 同步永远单向 cp -n + sha256 + 索引合并 + orphan 检查；同名冲突逐文件 diff 三分类，独有且缺失的内容带日期附录逐字追加，禁覆盖。
- 进备份仓库前密钥扫描；不写密钥/隐私；群聊不引用私人条目。

## 适用范围

本机多 Agent 共享记忆。换机器要改路径与接线面；WorkBuddy/豆包等 app 管理记忆的 Agent 无文件接线面，只能手动读。

## 剩余风险

- 国内版 23 个 stale 副本未覆盖（no-clobber 铁律），用户可选刷新；共享库已是更丰富版本。
- Qoder 国际版源库索引仍漏 5 条（源只读未改）；共享库索引已补全。
- WorkBuddy/豆包未接线；Gemini CLI 已卸载无 `.gemini`。

## 关联

- [[规则-国内版与国际版Qoder两套记忆目录完全独立只能单向拷入并校验]]
- [[规则-本机技能默认只开两个由总路由按需读取]]
- [[规则-本地手册接入DSH成为默认前置与写Markdown的编码坑]]
- [[规则-任务区与手册一体化联动]]
