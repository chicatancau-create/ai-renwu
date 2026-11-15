"""Regenerate D:\\Skills\\README.md (stale: still says 21 skills / old junction layout)
and create THIRD_PARTY.md - an honest provenance + licence register built from
frontmatter fields, .skill-lock.json and existing PROVENANCE.md files.
Nothing is invented: unknown sources are recorded as unknown.
"""
import json
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(errors="replace")
LIB = r"D:\Skills"
QT = r"D:\QoderToolkit"
ACTIVE = r"D:\Skills-active"
APPLY = "--apply" in sys.argv


def fm_of(p):
    t = open(p, encoding="utf-8", errors="replace").read()
    if not t.startswith("---"):
        return {}, t
    e = t.find("\n---", 3)
    raw, body = t[3:e], t[e + 4:]
    fm, key = {}, None
    for ln in raw.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", ln)
        if m:
            key, val = m.group(1), m.group(2).strip()
            fm[key] = "" if val in ("|", ">", "|-", ">-") else val.strip("'\"")
        elif key and ln.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " + ln.strip()).strip()
    return fm, body


def reparse(p):
    try:
        return getattr(os.lstat(p), "st_reparse_tag", 0)
    except OSError:
        return 0


skills = []
for n in sorted(os.listdir(LIB)):
    p = os.path.join(LIB, n)
    if reparse(p) or not os.path.isdir(p):
        continue
    sm = os.path.join(p, "SKILL.md")
    if not os.path.isfile(sm):
        continue
    fm, body = fm_of(sm)
    files = sum(len(f) for _, _, f in os.walk(p))
    byts = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(p) for f in fs)
    lic = [f for _, _, fs in os.walk(p) for f in fs if f.upper().startswith(("LICENSE", "NOTICE"))]
    prov = any(f.upper().startswith("PROVENANCE") for _, _, fs in os.walk(p) for f in fs)
    skills.append(dict(dir=n, name=fm.get("name", n), desc=fm.get("description", ""),
                       homepage=fm.get("homepage", ""), license=fm.get("license", ""),
                       author=fm.get("author", ""), version=fm.get("version", ""),
                       files=files, bytes=byts, lic_files=lic, provenance=prov))

lock = {}
lp = r"C:\Users\Admin\.agents\.skill-lock.json"
if os.path.isfile(lp):
    lock = json.load(open(lp, encoding="utf-8")).get("skills", {})

SELF = {"fs-fullstack", "fs-plan", "fs-scaffold", "fs-frontend", "fs-frontend-ui", "fs-backend",
        "fs-database", "fs-testing", "fs-security", "fs-code-review", "fs-performance",
        "fs-deploy", "fs-docs", "vision-tool", "local-ai-handbook", "windows-gui-control",
        "xd-authoring", "obsidian-vault-validation", "skill-router", "headroom"}

# Hard evidence gathered by probe_provenance.py / probe_qoder_push.py.
# Every entry cites where it came from; nothing here is inferred from a name.
EVIDENCE = {
    "docx": ("Anthropic 官方文档技能；OpenClaw 预装（`.clawx-preinstalled.json` slug=docx，"
             "2026-08-11，version=b29e7cf6…）",
             "**专有** `LICENSE.txt`：© 2025 Anthropic, PBC. All rights reserved.（禁止在 Services 外保留副本 / 转移第三方）"),
    "pdf": ("Anthropic 官方文档技能；OpenClaw 预装（slug=pdf，2026-08-11，version=b29e7cf6…）",
            "**专有** © 2025 Anthropic, PBC.（同 docx）"),
    "pptx": ("Anthropic 官方文档技能；OpenClaw 预装（slug=pptx，2026-08-11，version=b29e7cf6…）",
             "**专有** © 2025 Anthropic, PBC.（同 docx）"),
    "xlsx": ("Anthropic 官方文档技能；OpenClaw 预装（slug=xlsx，2026-08-11，version=b29e7cf6…）",
             "**专有** © 2025 Anthropic, PBC.（同 docx）"),
    "skill-creator": ("WorkBuddy 市场（`_skillhub_meta.json` skillId=skill_2053082698440450048，v0.2.0）",
                      "Apache-2.0（随包 `LICENSE.txt` 全文）"),
    "darwin-skill": ("WorkBuddy 市场（skillId=skill_2053081519859650560，v1.0.0）；"
                     "正文上游 URL `github.com/alchaincyf/darwin-skill`", "**未声明**"),
    "fullstack-dev": ("WorkBuddy 市场（skillId=skill_2053082011994116096，v1.0.0）", "MIT（frontmatter `license`）"),
    "github": ("WorkBuddy 市场（skillId=skill_2053082027691548672，v1.0.0）", "**未声明**"),
    "ios-application-dev": ("WorkBuddy 市场（skillId=skill_2053082181124681728，v1.0.0）", "MIT（frontmatter `license`）"),
    "impeccable": ("WorkBuddy 市场（skillId=skill_2053082862415904768，v2.0.0）；"
                   "frontmatter `homepage: github.com/pbakaus/impeccable`；"
                   "正文引用 `anthropics/skills` 的 frontend-design",
                   "Apache-2.0（frontmatter 声明，基于 Anthropic frontend-design）。"
                   "**瑕疵：声明「See NOTICE.md」但包内无 NOTICE.md**"),
    "brave-web-search": ("OpenClaw 预装（slug=brave-web-search，2026-08-11，version=3e088af6…）", "**未声明**"),
    "tavily-search": ("OpenClaw 预装（slug=tavily-search，2026-08-11，version=ea5e8201…）", "**未声明**"),
    "find-skills": ("OpenClaw 预装（slug=find-skills，2026-08-11，version=e173b8c8…）", "**未声明**"),
    "self-improving-agent": ("OpenClaw 预装（slug=self-improving-agent，2026-08-11，version=114ca7b5…）；"
                             "正文上游 `github.com/pskoett/pskoett-ai-skills`（v4.0.0）", "**未声明**"),
    "sickn33-frontend-slides": ("skillstore slug `sickn33-frontend-slides`（2026-10-02）；"
                                "frontmatter `source: github.com/zarazhangrui/frontend-slides`", "**未声明**"),
    "dws": ("钉钉官方 DingTalk Workspace CLI（随包 `NOTICE`：Copyright 2026 Alibaba Group）",
            "Apache-2.0（随包 `LICENSE` + `NOTICE`）"),
    "webapp-building": ("**泄露内容**：与 `D:\\QoderToolkit\\web-kimi` 逐文件 sha256 比对 173/175 字节相同；"
                        "web-kimi 的 PROVENANCE 记来源 `QvvvvvvQ/skills_leaks` 的 `Kimi/skills/webapp-building`",
                        "**没有任何使用许可**（上游 README 明示）。仅本机学习研究，禁止二次分发"),
    "reverse-trace": ("本机下载包 `H:\\下载\\06-skill-mcp-3.0\\trace（skill）.zip`（第三方分发，非官方市场）",
                      "**包内无 LICENSE，许可状态未知**；PROVENANCE 限定仅本机自用"),
    "reverse-wechat-miniapp": ("本机下载包 `H:\\下载\\06-skill-mcp-3.0\\wechat-miniapp-reverse(小程序逆向skill).zip`",
                               "**包内无 LICENSE，许可状态未知**；PROVENANCE 限定仅本机自用"),
    "landing-page-design": ("`github.com/elayadesign/ai-design-skills` @ `456d9e0d3e2d`（2026-11-01），见 PROVENANCE.md",
                            "MIT（随包 `LICENSE`，Copyright (c) 2026 Elaya）"),
    "figma-designer": ("`github.com/elayadesign/ai-design-skills` @ `456d9e0d3e2d`（2026-11-01），见 PROVENANCE.md",
                       "MIT（随包 `LICENSE`，Copyright (c) 2026 Elaya）"),
    "headroom": ("`github.com/headroomlabs-ai/headroom` 的 `skills/headroom/SKILL.md` 原文 + 本机安装事实段",
                 "Apache-2.0（上游仓库）"),
    "diagnose-windows-sandbox-acl": ("2026-11-15 01:38 由外部放入本库（DSH 侧技能）；**上游未记录**", "**未声明**"),
}

print("=== provenance evidence per skill ===")
rows = []
for s in skills:
    if s["dir"] in EVIDENCE:
        origin, lic = EVIDENCE[s["dir"]]
    elif s["dir"] in SELF:
        origin, lic = "本机自建", "自有"
    elif s["provenance"]:
        origin, lic = "见 PROVENANCE.md", "**未声明**"
    elif s["dir"] in lock:
        origin = "skillstore slug `%s`（%s 装入）" % (
            lock[s["dir"]].get("slug", s["dir"]), lock[s["dir"]].get("installedAt", "?")[:10])
        lic = s["license"] or "**未声明**"
    else:
        origin, lic = "**来源未记录**", s["license"] or "**未声明**"
    rows.append((s, origin, lic))
    print("  %-38s %s" % (s["dir"], lic[:70]))

# ---------------- THIRD_PARTY.md ----------------
tp = []
tp.append("# 第三方技能来源与许可登记\n")
tp.append("生成时间：%s。本文由脚本从 **frontmatter 字段 / `.agents\\.skill-lock.json` / 各技能自带的 "
          "`PROVENANCE.md` 与 `LICENSE`** 汇总，**没有推测来源**；查不到的就写「来源未记录」。\n"
          % time.strftime("%Y-%m-%d %H:%M"))
tp.append("\n> 本仓库是**个人备份**，不是再分发。下面标「未声明」的技能，其授权状态未知，"
          "**不要公开转发或商用**。\n")
tp.append("\n## 一、本机自建（%d 个）\n" % sum(1 for s, o, l in rows if o == "本机自建"))
tp.append("\n| 目录 | 说明 |\n| --- | --- |\n")
for s, o, l in rows:
    if o == "本机自建":
        tp.append("| `%s` | %s |\n" % (s["dir"], s["desc"][:70].replace("|", "/")))
tp.append("\n## 二、第三方引入（%d 个）\n" % sum(1 for s, o, l in rows if o != "本机自建"))
tp.append("\n| 目录 | frontmatter name | 来源 | 许可 | 自带 LICENSE |\n| --- | --- | --- | --- | --- |\n")
for s, o, l in rows:
    if o == "本机自建":
        continue
    tp.append("| `%s` | `%s` | %s | %s | %s |\n" % (
        s["dir"], s["name"], o.replace("|", "/"), l.replace("|", "/"),
        "有" if s["lic_files"] else "无"))
tp.append("\n## 三、目录名与 frontmatter `name` 不一致（已知例外，不要「顺手改」）\n")
tp.append("\n| 目录 | name | 为什么保留 |\n| --- | --- | --- |\n")
EXC = {
    "reverse-trace": "自带闸门 `scripts/validate_skill.py` 硬校验 name 必须是 `spider-king`，改了会多一条 ERROR",
    "reverse-wechat-miniapp": "与上游包名一致；Qoder 等按目录名登记，`reverse-` 前缀已足够区分",
    "brave-web-search": "上游 name 就是 `web-search`；目录名加了引擎前缀便于区分 tavily",
    "barnhardt-enterprises-inc-checkpoint": "skillstore slug 带厂商前缀，`.skill-lock.json` 按此 key 记录",
    "barry-liu-888-requirement-translator": "同上",
    "sickn33-frontend-slides": "同上",
}
for s in skills:
    if s["name"] != s["dir"]:
        tp.append("| `%s` | `%s` | %s |\n" % (s["dir"], s["name"], EXC.get(s["dir"], "历史原因，保留")))
tp.append("\n路由已验证：`router.py show <name>` 对上述每一个都能解析到正确目录，**不一致不影响使用**。\n")
tp.append("\n## 四、重复与分叉\n")
tp.append("\n- `D:\\Skills\\webapp-building` 与 `D:\\QoderToolkit\\web-kimi` **同名（name 都是 "
          "`webapp-building`）且同源**：175 个文件中 **173 个字节完全相同**，只有 `SKILL.md` 不同"
          "（4783 B vs 2537 B），前者多 `agents/openai.yaml`，后者多 `PROVENANCE.md`。\n"
          "  **没有合并**：`qoder-toolkit\\SKILL.md` 正文硬编码 `D:\\QoderToolkit\\web-kimi\\scripts\\template\\`，"
          "合并会打断 Qoder 侧路由。\n"
          "  **2026-11-15 修**：`D:\\Skills\\webapp-building` 原本丢掉了限制条款，已补 `PROVENANCE.md`。\n")
tp.append("\n## 五、被排除在 git 远端备份之外的技能\n")
tp.append("\n下列技能**仍在本地、仍可用，但永远不会被 push**（`.gitignore` 已按目录排除）。"
          "完整依据与重新取得方式见 `BACKUP_SCOPE.md`。\n")
tp.append("\n| 技能 | 原因 |\n| --- | --- |\n")
for d, why in (("docx", "Anthropic 专有：禁止在 Services 之外保留副本、禁止转移第三方"),
               ("pdf", "同上"), ("pptx", "同上"), ("xlsx", "同上"),
               ("reverse-trace", "无 LICENSE，PROVENANCE 限定仅本机自用、不二次分发"),
               ("reverse-wechat-miniapp", "同上"),
               ("webapp-building", "泄露的 Kimi 产品技能，上游明示没有任何使用许可")):
    tp.append("| `%s` | %s |\n" % (d, why))
tp.append("\n**私有仓库不能解决这一条**：上传到托管平台本身就是「转移给第三方」。\n")
tp.append("\n## 六、已知瑕疵（不编造修补）\n")
tp.append("\n- `impeccable` frontmatter 写「See NOTICE.md for attribution」，但包内**没有 NOTICE.md**"
          "（实测目录只有 `SKILL.md`、`_icon.png`、`_skillhub_meta.json`、`references`）。"
          "上游包自带的断引用，**没有伪造署名文件**。\n")
tp_text = "".join(tp)

# ---------------- README.md ----------------
rd = []
rd.append("# D:\\Skills — 本机 AI 智能体统一技能库\n\n")
rd.append("所有 Agent 共用这一份技能实体。**本目录是唯一真源**，各工具通过目录联接（Junction）接入。\n\n")
rd.append("> 本仓库同时是备份：GitHub + GitCode 双远端。恢复方法见文末。\n\n")
rd.append("## 一、两层结构（默认只开两个）\n\n")
rd.append("| 目录 | 角色 |\n| --- | --- |\n")
rd.append("| `D:\\Skills` | **全量库**，%d 个技能实体，唯一真源 |\n" % len(skills))
rd.append("| `D:\\Skills-active` | **默认窗口**，只放 `headroom` + `skill-router` 两条联接 |\n")
rd.append("| `D:\\Skills-disabled` | 停用区，不参与自动发现，保留可恢复源文件 |\n\n")
rd.append("各 Agent 的技能根指向 **`D:\\Skills-active`**，所以任何 Agent 启动时只加载两个技能：\n\n")
rd.append("1. **`skill-router`** — 判断本次任务需要哪些技能，然后**直接 read `D:\\Skills\\<目录>\\SKILL.md`**。\n")
rd.append("2. **`headroom`** — 省 token（压缩送进 LLM 的工具输出），常驻代理 `127.0.0.1:8787`。\n\n")
rd.append("**为什么用「读文件」而不是「改目录」**：多数 Agent 在会话开始时快照技能列表，"
          "会话中改目录看不见；读文件任何 Agent 都即时生效，而且其他技能的 description 永不进上下文。\n\n")
rd.append("## 二、当前联接（实测）\n\n")
rd.append("| Agent 技能根 | 形态 | 指向 |\n| --- | --- | --- |\n")
ROOTS = [
    ("Claude Code", r"C:\Users\Admin\.claude\skills"),
    ("DSH / Agents 规范", r"C:\Users\Admin\.agents\skills"),
    ("OpenCode", r"C:\Users\Admin\.config\opencode\skills"),
    ("WorkBuddy 国内版", r"C:\Users\Admin\.workbuddy\skills"),
    ("WorkBuddy 国际版", r"C:\Users\Admin\.workbuddy-ai\skills"),
    ("OpenClaw", r"C:\Users\Admin\.openclaw\skills"),
    ("Codex", r"C:\Users\Admin\.codex\skills"),
    ("Qoder", r"C:\Users\Admin\.qoder\skills"),
    ("Qoder CN", r"C:\Users\Admin\.qoder-cn\skills"),
    ("Herdsman", r"C:\Users\Admin\.herdsman\work\skills"),
    ("DSH 私有", r"C:\Users\Admin\.dsh\skills"),
    ("cc-switch", r"C:\Users\Admin\.cc-switch\skills"),
]
for label, p in ROOTS:
    if not os.path.exists(p):
        rd.append("| %s | 不存在 | — |\n" % label)
        continue
    tag = reparse(p)
    if tag:
        try:
            tgt = os.readlink(p).replace("\\\\?\\", "")
        except OSError:
            tgt = "?"
        rd.append("| %s | 整目录 Junction | `%s` |\n" % (label, tgt))
    else:
        kids = [n for n in os.listdir(p) if os.path.isdir(os.path.join(p, n))]
        rd.append("| %s | 真实目录，%d 个条目 | 逐项联接 |\n" % (label, len(kids)))
rd.append("\n## 三、⚠️ 联接的毁灭点（已经踩三次）\n\n")
rd.append("**联接给了唯一真源，也给了唯一毁灭点。**\n\n")
rd.append("用资源管理器删除 / 批量搬迁工具「移动」任一 Agent 技能根里的联接时，"
          "**Windows shell 会跟随联接，把 `D:\\Skills` 里的真源一起删掉**。\n\n")
rd.append("已发生：2026-11-15 02:04:06、02:22:56、02:23:43 三次，"
          "`headroom` 与 `skill-router` 全部文件被回收。\n\n")
rd.append("**纪律**：\n\n")
rd.append("- 停用技能 → 移到 `D:\\Skills-disabled`，**不要删 `D:\\Skills-active` 里的条目**。\n")
rd.append("- 批量搬迁 Agent 数据目录前 → 先摘掉技能根里的联接，或先把本库复制到搬迁范围外。\n")
rd.append("- 判据：**文件进了回收站 ⇒ 是 shell 删的，不是 Python `rmtree`**（后者不进回收站）。\n")
rd.append("- 兜底：`skill_shield.py` 每 20 秒自愈一次，但**刚写还没镜像的内容仍会丢**；"
          "真正的兜底是本仓库的 git 远端。\n\n")
rd.append("## 四、技能清单（%d 个）\n\n" % len(skills))
EXCLUDED = {"docx", "pdf", "pptx", "xlsx", "reverse-trace", "reverse-wechat-miniapp",
            "webapp-building"}
rd.append("标 LOCK 的**不进 git 远端备份**（许可禁止再分发），仍在本地可用；依据见 `BACKUP_SCOPE.md`。\n")
groups = [
    ("全栈开发流水线 fs-*（13 个，自建）", lambda s: s["dir"].startswith("fs-")),
    ("前端 / 设计 / 演示", lambda s: s["dir"] in (
        "webapp-building", "impeccable", "sickn33-frontend-slides", "landing-page-design",
        "figma-designer", "darwin-skill", "fullstack-dev", "ios-application-dev")),
    ("文档 / 表格 / 检索", lambda s: s["dir"] in (
        "docx", "xlsx", "pptx", "pdf", "brave-web-search", "tavily-search", "github", "find-skills")),
    ("本机运维 / 自建工具", lambda s: s["dir"] in (
        "skill-router", "headroom", "local-ai-handbook", "windows-gui-control", "xd-authoring",
        "vision-tool", "obsidian-vault-validation", "diagnose-windows-sandbox-acl",
        "self-improving-agent", "skill-creator")),
    ("需求 / 进度", lambda s: s["dir"] in (
        "barry-liu-888-requirement-translator", "barnhardt-enterprises-inc-checkpoint")),
    ("钉钉", lambda s: s["dir"] == "dws"),
    ("逆向（仅授权目标）", lambda s: s["dir"].startswith("reverse-")),
]
seen = set()
for title, pred in groups:
    sel = [s for s in skills if pred(s) and s["dir"] not in seen]
    if not sel:
        continue
    for s in sel:
        seen.add(s["dir"])
    rd.append("\n### %s\n\n| 目录 | 用途 |\n| --- | --- |\n" % title)
    for s in sel:
        d = s["desc"].replace("|", "/").replace("\n", " ")
        mark = " 🔒" if s["dir"] in EXCLUDED else ""
        rd.append("| `%s`%s | %s |\n" % (s["dir"], mark, d[:110]))
rest = [s for s in skills if s["dir"] not in seen]
if rest:
    rd.append("\n### 其他\n\n| 目录 | 用途 |\n| --- | --- |\n")
    for s in rest:
        rd.append("| `%s` | %s |\n" % (s["dir"], s["desc"].replace("|", "/")[:110]))
rd.append("\n## 五、第二个库：QoderToolkit\n\n")
rd.append("`D:\\QoderToolkit` → `D:\\_整理\\04-AI工具包\\QoderToolkit`（总联接，"
          "隔离「另一个 AI 还在搬 D:\\_整理」的风险）。10 个技能，其中 `ppt-master` 约 89 MB。\n\n")
rd.append("**为什么必须有 `D:\\QoderToolkit` 这层总联接**：`qoder-toolkit\\SKILL.md` 正文硬编码了\n")
rd.append("`D:\\QoderToolkit\\ppt-master\\SKILL.md`、`D:\\QoderToolkit\\web-taste\\SKILL.md`、\n")
rd.append("`D:\\QoderToolkit\\web-kimi\\scripts\\template\\`、"
          "`D:\\QoderToolkit\\ppt-master\\scripts\\attribution_guard.py` 四处路径。\n")
rd.append("只改 `.qoder\\skills` 的联接不够。它单独一个 git 仓库备份。\n\n")
rd.append("## 六、规则\n\n")
rd.append("1. 新技能放 `D:\\Skills\\<name>\\SKILL.md`，目录名小写字母数字连字符，**与 frontmatter `name` 同名**"
          "（已知例外见 `THIRD_PARTY.md`）。\n")
rd.append("2. `description` 必须说清**什么时候用**（触发词），长度 ≤1024 字符。\n")
rd.append("3. **运行时缓存 / 输出不得写入技能源目录**，用 `AI_SHARED_SKILLS_STATE_DIR`"
          "（本机 = `D:\\AI-Tool-State`）。\n")
rd.append("4. 第三方技能必须留 `PROVENANCE.md`（来源 / commit / 许可）；许可未知的标注清楚。\n")
rd.append("5. 新增或改动后跑 `python D:\\Skills\\skill-router\\router.py sync` 重建索引。\n")
rd.append("6. 不把框架 / 运行时 / 数据库 / 安全清单的版本写死；已有项目以仓库配置与锁文件为准。\n\n")
rd.append("## 七、日常运维\n\n")
rd.append("```powershell\n")
rd.append("$py = 'C:\\Users\\Admin\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe'\n")
rd.append("& $py D:\\Skills\\skill-router\\ops.py status    # 代理 / 接线 / 窗口 / 12 个技能根\n")
rd.append("& $py D:\\Skills\\skill-router\\ops.py savings   # headroom 真实省了多少\n")
rd.append("& $py D:\\Skills\\skill-router\\ops.py guard     # 接线守护\n")
rd.append("& $py D:\\Skills\\skill-router\\ops.py shield    # 自愈盾\n")
rd.append("& $py D:\\Skills\\skill-router\\router.py match \"这次任务描述\"\n")
rd.append("& $py D:\\Skills\\skill-router\\router.py doctor\n")
rd.append("```\n\n")
rd.append("## 八、从 git 恢复\n\n")
rd.append("```powershell\n")
rd.append("git clone https://github.com/chicatancau-create/ai-skills.git D:\\Skills\n")
rd.append("# 国内：git clone https://gitcode.com/zhoumoyukuai/ai-skills.git D:\\Skills\n")
rd.append("& $py D:\\Skills\\skill-router\\wire_agents.py --apply   # 重建默认窗口与各 Agent 联接\n")
rd.append("& $py D:\\Skills\\skill-router\\router.py sync\n")
rd.append("& $py D:\\Skills\\skill-router\\ops.py wire --apply      # 接回 headroom 省 token 链路\n")
rd.append("```\n\n")
rd.append("**注意**：`headroom` 的常驻代理与模型缓存不在本仓库里"
          "（`D:\\uv\\tools\\headroom-ai`、`D:\\uv\\data\\huggingface\\hub` 那 261 MB），"
          "恢复后需重跑 `seed_kompress.py` 与 `headroom install apply`，命令见 `headroom\\SKILL.md`。\n")
rd_text = "".join(rd)

for rel, text in (("THIRD_PARTY.md", tp_text), ("README.md", rd_text)):
    p = os.path.join(LIB, rel)
    old = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    print("\n%s %s  (%d -> %d B)" % ("WRITE" if APPLY else "would write", rel,
                                     len(old.encode()), len(text.encode())))
    if APPLY:
        if os.path.isfile(p):
            bk = r"G:\AIrenwu\_audit\optimize-backup-20261115-023537"
            os.makedirs(bk, exist_ok=True)
            import shutil
            shutil.copy2(p, os.path.join(bk, rel))
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
if not APPLY:
    print("\nDRY RUN - rerun with --apply")
