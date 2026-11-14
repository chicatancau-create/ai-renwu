# -*- coding: utf-8 -*-
"""生成 02-资料库-快照.md。数据来源: _lib_scan.collect() (只读)。
评论文字由扫描员基于真实读到的内容撰写; 文档宣称一律标注「宣称/未确认」。
体积护栏: <=80KB, 超限按 trim 级别砍 6/8 节样本, 保 1/2/3/4/5/7。
"""
import os, sys, re, json, datetime, subprocess, collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _lib_scan as S

ROOT = S.ROOT
OUT = r"G:\AIrenwu\02_项目代码\gemini-pack\02-资料库-快照.md"
LIMIT = 80_000  # 任务「≤80KB」按更严格的 80,000 字节口径执行
SEP = os.sep

FLAGS = []

def emb(text):
    if text is None:
        return None
    t, fl = S.mask(text)
    FLAGS.extend(fl)
    return t

def fence(text, lang=""):
    body = text if text is not None else "(未读到)"
    # 动态围栏：内容含 ``` 时用 ```` 包裹，避免嵌套围栏提前闭合（交接文档内有 ```bash）
    runs = re.findall(r"`{3,}", body)
    n = max((len(r) for r in runs), default=2) + 1
    bar = "`" * max(3, n)
    return bar + lang + "\n" + body + "\n" + bar

def ap(rel):
    return ROOT + "\\" + rel.replace("/", "\\")

def rehead(text, n):
    if text is None:
        return None
    lines = text.splitlines()
    if len(lines) <= n:
        return text
    return "\n".join(lines[:n]) + "\n…(已截断)"

def tracked_stats():
    """git ls-files -z: 只读索引, 不改 git 状态。-z 避免中文八进制转义。"""
    try:
        r = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"],
                           capture_output=True, timeout=120)
        if r.returncode != 0:
            return None
        names = [n.decode("utf-8", "replace") for n in r.stdout.split(b"\0") if n]
        total = 0; md = 0; missing = 0; n05 = 0; wb = 0
        for n in names:
            p = os.path.join(ROOT, n.replace("/", SEP))
            try:
                total += os.path.getsize(p)
            except OSError:
                missing += 1
            if n.lower().endswith(".md"):
                md += 1
            if n.startswith("05-外部资料库/"):
                n05 += 1
            if n.startswith(".workbuddy/"):
                wb += 1
        return {"count": len(names), "size": total, "md": md, "missing": missing, "n05": n05, "wb": wb}
    except Exception:
        return None

SCRIPT_PURPOSE = {
    "check_student_packages.mjs":
        "G0–G9 学生包结构门禁：检查十个包齐全（S01），每包必含 README.md、自评指南.md、参考答案/、自测脚本/、起始代码/、"
        "evidence/judge-solution.txt、evidence/judge-starter.txt；参考答案与自测脚本目录非空；统计 TODO 标记并检查其只出现在起始代码"
        "（todoOutsideStarter）。引用 06-实验代码/_template/manifest.mjs 作为 manifest 工具。",
    "verify_all.mjs":
        "总门禁聚合器：参数 --profile=quick|ci（默认 quick）、--offline、--practice-root= 或环境变量 PRACTICE_ROOT 指定外部练习仓。"
        "先跑 05-外部资料库/tools/catalog_tool.py validate --mode source-only，再按 PRACTICE_PROJECTS 清单（前 30 行可见 P01=project01-blog、"
        "P02=project02-collab、B5-01=project02-spring，后续被截断）到外部仓逐项目校验。README/交接文档宣称含两仓秘密扫描；本次未复跑。",
    "verify_archive.sh":
        "从两仓 git archive HEAD 的已提交内容复核（解包到临时目录后跑 source-only + 14 个实验 manifest + 8 个外部项目 manifest），"
        "防止工作区未提交/被忽略文件造成假绿。默认 VAULT_ROOT=/e/OBsidian/全栈工程师学习资料库、PRACTICE_ROOT=/e/fullstack-code。"
        "含 Windows Git Bash mktemp 盘符导致 trap 误失败的修复注释（cygpath 转换）。",
}

def build(D, trim=0):
    fset = {r for r, _, _ in D["files"]}
    def exists(rel):
        return rel.replace("/", SEP) in fset

    ts = tracked_stats()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_total = len(D["md_files"])
    fm_total = D["fm_yes"] + D["fm_no"]
    own_md = sum(len(v) for k, v in D["md_by_dir"].items() if k != "05-外部资料库")
    own_fm = sum(n for k, n in D["fm_by_top"].items() if k != "05-外部资料库")
    own_code = D["code_count"] - D["dir_code"].get("05-外部资料库", 0)

    # manifest 分类
    own_mf = [(p, s) for p, s in D["manifests"] if not p.startswith("05-外部资料库" + SEP)]
    ext_mf = [(p, s) for p, s in D["manifests"] if p.startswith("05-外部资料库" + SEP)]
    core_mf = [(p, s) for p, s in own_mf
               if os.path.basename(p) == "manifest.json" and os.path.basename(os.path.dirname(p)) == "evidence"]
    aux_mf = [(p, s) for p, s in own_mf if (p, s) not in core_mf]
    core_by_top = collections.Counter(p.split(SEP)[0] for p, _ in core_mf)
    idx_out = [(p, s) for p, s in D["index_jsons"] if not p.startswith("05-外部资料库" + SEP)]
    weave_hits = [r for r in fset if "weave" in os.path.basename(r).lower()]

    # 08 有 fm 的 17 份分布(复核「都是语料数据」的说法)
    fm08 = []
    for rel in D["md_by_dir"].get("08-判定题库", []):
        t = S.read_text(os.path.join(ROOT, rel))
        fm, _ = S.fm_parse(t)
        if fm is not None:
            fm08.append(rel)
    fm08_dist = collections.Counter(SEP.join(r.split(SEP)[:3]) for r in fm08)
    rag_prefix = "08-判定题库" + SEP + "专题题库" + SEP + "RAG-GoldenSet"
    rag_only = bool(fm08) and all(r.startswith(rag_prefix) for r in fm08)
    core_match = (len(core_mf) == 29 and core_by_top.get("01-阶段课程") == 9
                  and core_by_top.get("06-实验代码") == 14 and core_by_top.get("08-判定题库") == 6)

    # 体积阶梯: 先砍可选证据(脚本头/冗余表/重复样本/6、8节样本),
    # 保 lead 指定内容(workflow 前25行、交接前120行)与 1/2/3/4/5/7 必备项;
    # trim=3 才动 workflow/交接行数(硬上限兜底)。
    q_lines = 40 if trim == 0 else (24 if trim == 1 else 14)
    colo_cap = 40
    wf_lines = 25 if trim < 3 else 12
    hand_lines = 120 if trim < 3 else 60
    script_heads = (trim == 0)
    u01_sample = (trim == 0)
    per_top_table = (trim == 0)
    ext_n = 40 if trim == 0 else (25 if trim == 1 else 12)
    field_n = 40 if trim == 0 else (25 if trim == 1 else 10)
    ext_mf_n = 5 if trim == 0 else (3 if trim == 1 else 2)
    p07_lines = None if trim == 0 else (30 if trim == 1 else 20)
    wf_short = (trim >= 1)
    core01_pattern = (trim >= 1)

    L = []
    A = L.append

    # ================= 头部 =================
    A("# 全栈工程师学习资料库 · 仓库快照报告")
    A("")
    A("- 生成时间：%s（本机本地时间）" % now)
    A("- 扫描对象：`%s`（工作区现状，含未提交改动；非 HEAD 提交树）" % ROOT)
    A("- 扫描方式：只读。Python `os.walk` 全量遍历 + 逐文件读取（`utf-8-sig, errors=replace`）；git 信息来自 `.git/config`、`.git/HEAD`、`.git/refs` 与只读命令 `git log -3`、`git ls-files -z`。未修改仓库内任何文件，未执行任何改变 git 状态的命令，未复跑任何门禁脚本。")
    A("- 排除目录：`.git`（单独计大小）、`.obsidian`（实测不存在）、`node_modules`、`__pycache__`。")
    A("- 脱敏：URL 内嵌凭据、常见 token 模式（ghp_/github_pat_/sk-/AKIA/xox/glpat）、邮箱、中国大陆手机号 → `***`。本次全部嵌入文本命中数：{PII_COUNT}。")
    A("- 路径约定：正文引用用绝对路径；目录树与文件清单为仓库相对路径（根 = `%s`）。" % ROOT)
    A("- 判定口径：frontmatter = 文件首行 `---` 且 200 行内出现闭合 `---`/`...`；链接计数用正则，markdown 链接含图片嵌入 `![](...)`；>2MB 的 md 跳过链接计数（本次 %d 个）。代码扩展名集合见第 3 节。" % D["big_skipped"])
    A("- 本报告供 Gemini 做双仓架构分析（CodeWeave 主软件 + 本资料库）。所有「宣称」均来自仓库内文档原文（已嵌入），扫描员未独立验证；判不了的写「未确认」。")
    A("")
    A("## 执行摘要（扫描员结论，依据见对应章节）")
    A("")
    A("1. **规模极度偏斜**：工作区 %s 个文件 / %s，其中 `05-外部资料库` 占 md %s/%s（%.1f%%）、代码 %s/%s、体积 %s。该目录的 题库/ 与 知识库/ 被 `.gitignore` 整体排除（本地镜像，不进 Git）。自有内容仅 md %d 篇、代码 %d 个。任何全局索引方案必须先分层处理 05。" % (
        format(D["total_files"], ","), S.fmt_size(D["total_size"]),
        format(len(D["md_by_dir"].get("05-外部资料库", [])), ","), format(md_total, ","),
        100.0 * len(D["md_by_dir"].get("05-外部资料库", [])) / max(md_total, 1),
        format(D["dir_code"].get("05-外部资料库", 0), ","), format(D["code_count"], ","),
        S.fmt_size(D["dir_size"].get("05-外部资料库", 0)), own_md, own_code))
    fm08_claim = ("全部是 RAG-GoldenSet 判定题语料数据文件（字段 id/tenant/title/version），不是学习笔记"
                  if rag_only else "分布见 5.1（均为题库数据文件，非学习笔记元数据）")
    A("2. **自有学习笔记 frontmatter 覆盖率 ≈ 0%%**：全库 fm 覆盖 %.1f%%（%s/%s）几乎全部来自 05 外部抓取内容（%s 篇）；01/02/06/07 四个自有目录 0 篇有 fm；08 的 %d 篇有 fm 者%s。Gemini 建议的 stack/sandbox_path/related_ids 字段全库 0 命中。" % (
        100.0 * D["fm_yes"] / max(fm_total, 1), format(D["fm_yes"], ","), format(fm_total, ","),
        format(D["fm_by_top"].get("05-外部资料库", 0), ","), own_fm, fm08_claim))
    A("3. **无知识索引**：`scripts/build-index.js` 不存在；全库无 weave-index.json；仓内 %d 个 *manifest*.json 中自有的 %d 个是「实验证据清单」（命令退出码+文件 sha256），不是知识点索引，与 Gemini 建议的 manifest.json 用途不同（详见第 3 节）。" % (len(D["manifests"]), len(own_mf)))
    A("4. **同地性已部分实现**：06-实验代码 每个实验单元自包含 README+src/tests/scripts/evidence（同目录）；07-项目实现 已清空为纯索引，P02/P03/P04 真实源码在外部仓 `E:\\fullstack-code`（实测存在，内容未扫描）。")
    A("5. **CI 名存实亡**：`.github/workflows` 有 12 个 workflow；README 宣称全部从未在 Actions 实跑，2026-11-08 起计费阻断（交接文档引 annotation 原文）。「全绿」仅指本机门禁，且本次未复跑。")
    A("")

    # ================= 1 仓库概览 =================
    A("## 1. 仓库概览")
    A("")
    A("| 项 | 值 |")
    A("| --- | --- |")
    A("| 本地路径 | `%s` |" % ROOT)
    A("| 当前分支 | `%s`（读 .git/HEAD） |" % D["branch"])
    A("| 分支 HEAD | `%s`（读 .git/refs/heads/…） |" % (D["branch_sha"] or "未确认"))
    A("| .obsidian | %s |" % ("存在" if D["obsidian_exists"] else "不存在（实测；.gitignore 仍保留其缓存忽略规则）"))
    A("| 外部代码仓 `E:\\fullstack-code` | %s（仅存在性探测，内容未扫描——任务边界） |" % D["fullstack_code"])
    A("| 遍历错误 | %d 个（os.walk onerror 收集；0 = 无权限拒绝，「不存在」结论可信） |" % len(D["walk_errors"]))
    A("| .git 体积 | %s |" % S.fmt_size(D["git_size"]))
    if ts:
        A("| Git 跟踪文件 | %s 个（git ls-files -z），其中 md %s 个；按工作区现状合计 %s%s |" % (
            format(ts["count"], ","), format(ts["md"], ","), S.fmt_size(ts["size"]),
            "；%d 个跟踪文件在工作区缺失" % ts["missing"] if ts["missing"] else ""))
    else:
        A("| Git 跟踪文件 | 未确认（git ls-files 不可用） |")
    A("")
    A("远端（读 `.git/config`；已按规则脱敏，本次未发现内嵌凭据）：")
    A("")
    A("| remote | URL |")
    A("| --- | --- |")
    for name, url in D["git_remotes"]:
        A("| %s | `%s` |" % (name, emb(url)))
    if D["git_proxy"]:
        A("")
        for u, p in D["git_proxy"]:
            A("另有按域代理配置：`http.%s.proxy = %s`（本机代理，非凭据）。" % (u, p))
    A("")
    A("最近 3 条提交（来源：%s）：" % D["commits_src"])
    A("")
    if D["commits"]:
        A("| hash | 日期 | subject |")
        A("| --- | --- | --- |")
        for h, d, s in D["commits"]:
            A("| `%s` | %s | %s |" % (h, d, emb(s)))
    else:
        A("未确认（git log 与 reflog 回退均不可用）。")
    A("")
    A("注意：交接文档警告「资料库工作区可能有其他会话（豆包/ASR）的未提交改动」（原文见附录 A）。本报告统计工作区现状；未做工作区 vs HEAD 差异比对（避免触发会写 .git/index 的 git 命令）。")
    A("")

    # ================= 2 目录树 =================
    A("## 2. 目录树（深度 3，排除 .git/.obsidian/node_modules/__pycache__）")
    A("")
    A("一级/二级目录标注 `[md:n code:n]`（该目录递归累计）；一级目录另标体积。深度 3 仅列目录名。")
    A("")
    A("```")
    A(ROOT + "\\")
    tree_lines = []
    def show(node, prefix, depth, relprefix):
        items = sorted(node.items())
        for i, (name, sub) in enumerate(items):
            if i >= 40:
                tree_lines.append(prefix + "… 另有 %d 个目录未展开" % (len(items) - 40))
                break
            rel = (relprefix + "/" + name) if relprefix else name
            key = rel.replace("/", SEP)
            ann = ""
            if depth <= 2:
                ann = "  [md:%d code:%d]" % (D["dir_md"].get(key, 0), D["dir_code"].get(key, 0))
                if depth == 1:
                    ann += " %s" % S.fmt_size(D["dir_size"].get(key, 0))
            tree_lines.append(prefix + name + "/" + ann)
            if depth < 3:
                show(sub, prefix + "  ", depth + 1, rel)
    show(D["tree"], "", 1, "")
    L.extend(tree_lines)
    A("```")
    A("")
    root_files = [(r, s) for r, s, _ in D["files"] if SEP not in r]
    A("根目录文件：%s。" % "、".join("`%s`(%s)" % (r, S.fmt_size(s)) for r, s in sorted(root_files)))
    A("")
    A("要点：`05-外部资料库/题库`、`05-外部资料库/知识库` 为 .gitignore 排除的本地镜像（第 9 节）；`07-项目实现` 只有一个 README.md（纯索引）；`06-实验代码` 的 build/、dist/ 产物也被忽略（工作区可见但不入库）。")
    A("")

    # ================= 3 全库统计 =================
    A("## 3. 全库统计")
    A("")
    A("| 指标 | 值 |")
    A("| --- | --- |")
    A("| 文件总数（工作区，排除目录后） | %s |" % format(D["total_files"], ","))
    A("| 总大小（工作区） | %s（另 .git %s） |" % (S.fmt_size(D["total_size"]), S.fmt_size(D["git_size"])))
    A("| .md 总数 | %s |" % format(md_total, ","))
    A("| 代码文件数 | %s |" % format(D["code_count"], ","))
    A("| 附件数（图片/文档/压缩包/字体等） | %s |" % format(D["attach_count"], ","))
    A("| 自有内容（除 05 外） | md %d 篇、代码 %d 个 |" % (own_md, own_code))
    A("")
    A("代码扩展名集合（统计口径）：%s。附件集合：%s。`.ipynb`/`.json`/`.csv` 等归「其他」。" % (
        " ".join(sorted(S.CODE_EXTS)), " ".join(sorted(S.ATTACH_EXTS))))
    A("")
    A("按扩展名计数（Top %d%s）：" % (ext_n, "，完整分布可由 _lib_scan.py 复现" if ext_n < 40 else ""))
    A("")
    A("| 扩展名 | 数量 | 类别 |")
    A("| --- | --- | --- |")
    for e, n in D["ext_hist"].most_common(ext_n):
        cat = "笔记" if e == ".md" else ("代码" if e in S.CODE_EXTS else ("附件" if e in S.ATTACH_EXTS else "其他"))
        A("| %s | %s | %s |" % (e, format(n, ","), cat))
    A("")
    if per_top_table:
        A("按一级目录（md/代码/体积）：")
        A("")
        A("| 一级目录 | md | 代码 | 体积 |")
        A("| --- | --- | --- | --- |")
        for k in sorted(D["md_by_dir"]):
            if SEP in k:
                continue
            A("| %s | %s | %s | %s |" % (k, format(len(D["md_by_dir"][k]), ","),
                                         format(D["dir_code"].get(k, 0), ","), S.fmt_size(D["dir_size"].get(k, 0))))
        A("")
    else:
        A("按一级目录的 md/代码/体积见第 2 节目录树一级标注（体积纪律：此处不重复列表）。")
        A("")
    A("### 3.1 索引文件搜索结果")
    A("")
    A("- 搜索方式：全量文件清单按 basename 匹配 `*manifest*.json` 与 `*index*.json`（排除 node_modules 等）。")
    A("- `*manifest*.json`：**%d 个** = 自有 %d 个 + 05 外部仓自带 %d 个（后者是第三方项目自己的文件，与知识索引无关）。" % (len(D["manifests"]), len(own_mf), len(ext_mf)))
    A("- `*index*.json`：**%d 个**，其中 05 外部 %d 个、自有 %d 个。%s" % (
        len(D["index_jsons"]), len(D["index_jsons"]) - len(idx_out), len(idx_out),
        ("自有清单：" + "、".join("`%s`" % p for p, _ in idx_out)) if idx_out else "即：**本仓自有内容没有任何全局 index.json**。"))
    A("- `weave-index.json`：**未找到**（全库 basename 含 weave 的文件 %d 个）。" % len(weave_hits))
    A("- `scripts/build-index.js`：**不存在**（实测）。Gemini 建议的索引生成脚本尚未落地。")
    A("")
    A("### 3.2 自有 evidence/manifest.json（核心 %d 份，完整路径）" % len(core_mf))
    A("")
    A("分布：%s。与 `000-学习总览.md` §1.5 宣称「本仓库内共 29 份 evidence/manifest.json（01-阶段课程 9、06-实验代码 14、08-判定题库 6）」%s。" % (
        "、".join("%s %d 份" % (k, v) for k, v in sorted(core_by_top.items())),
        "**逐目录吻合**（实测核对）" if core_match else "**存在出入**（实测核对，以本节清单为准）"))
    A("")
    if core01_pattern:
        c01 = [(p, s) for p, s in core_mf if p.startswith("01-阶段课程" + SEP)]
        c06 = [(p, s) for p, s in core_mf if p.startswith("06-实验代码" + SEP)]
        c08 = [(p, s) for p, s in core_mf if p.startswith("08-判定题库" + SEP)]
        if c01:
            sizes = [s for _, s in c01]
            A("- `%s`（%s）；**U02–U09 另有 %d 份同构**，路径模式 `%s\\01-阶段课程\\教学单元\\U0X-<单元名>\\evidence\\manifest.json`（每份 %s–%s）" % (
                ap(c01[0][0]), S.fmt_size(c01[0][1]), len(c01) - 1, ROOT,
                S.fmt_size(min(sizes)), S.fmt_size(max(sizes))))
        for p, s in c06:
            A("- `%s`（%s）" % (ap(p), S.fmt_size(s)))
        zt = [(p, s) for p, s in c08 if (SEP + "专题题库" + SEP) in p]
        other = [(p, s) for p, s in c08 if (SEP + "专题题库" + SEP) not in p]
        if zt:
            A("- `%s`（%s）；**专题题库另有 %d 份同构**（SQL50/全英文面试10套/后端实操30），路径模式 `%s\\08-判定题库\\专题题库\\<专题>\\[真实环境\\]evidence\\manifest.json`" % (
                ap(zt[0][0]), S.fmt_size(zt[0][1]), len(zt) - 1, ROOT))
        for p, s in other:
            A("- `%s`（%s）" % (ap(p), S.fmt_size(s)))
    else:
        for p, s in core_mf:
            A("- `%s`（%s）" % (ap(p), S.fmt_size(s)))
    A("")
    A("自有辅助 manifest（非 evidence/manifest.json 命名，%d 份）：" % len(aux_mf))
    A("")
    if core01_pattern:
        aux90 = [(p, s) for p, s in aux_mf if p.startswith("90-历史归档" + SEP)]
        auxrest = [(p, s) for p, s in aux_mf if not p.startswith("90-历史归档" + SEP)]
        for p, s in auxrest:
            A("- `%s`（%s）" % (ap(p), S.fmt_size(s)))
        if aux90:
            dirs = set(os.path.dirname(p) for p, _ in aux90)
            if len(dirs) == 1:
                sizes = [s for _, s in aux90]
                names = "、".join(os.path.basename(p) for p, _ in aux90)
                A("- `%s` 目录下另有 %d 份：%s（历史归档快照，%s–%s，非知识索引）" % (
                    ap(os.path.dirname(aux90[0][0])), len(aux90), names,
                    S.fmt_size(min(sizes)), S.fmt_size(max(sizes))))
            else:
                for p, s in aux90:
                    A("- `%s`（%s）" % (ap(p), S.fmt_size(s)))
    else:
        for p, s in aux_mf:
            A("- `%s`（%s）" % (ap(p), S.fmt_size(s)))
    A("")
    A("05 外部仓自带的 %d 个 manifest 示例（其余略，完整清单可由脚本复现）：" % len(ext_mf))
    A("")
    for p, s in ext_mf[:ext_mf_n]:
        A("- `%s`（%s）" % (ap(p), S.fmt_size(s)))
    A("")
    A("### 3.3 README 宣称的「17 份 manifest」对账")
    A("")
    A("README 宣称「E01–E13 + G1 + P02/P03/P04 共 17 份 manifest 全部校验通过」。对账：")
    A("")
    A("- 仓内 14 份（E01–E13 各 1 + G1 1）：**实测存在**，路径见 3.2 的 06-实验代码部分。")
    A("- 外部 3 份（P02/P03/P04）：**不在本仓**（全库无 P0* 路径的 manifest，实测）。07-项目实现/README.md 宣称其位于外部仓，推定路径如下（**未确认**，外部仓内容不在扫描范围）：")
    A("  - `E:\\fullstack-code\\projects\\project02-collab\\evidence\\manifest.json`")
    A("  - `E:\\fullstack-code\\projects\\project03-trade\\evidence\\manifest.json`")
    A("  - `E:\\fullstack-code\\projects\\project04-saas\\evidence\\manifest.json`")
    A("- 总览另宣称外部仓共 8 份 manifest（含 P01/P05/变体项目）：**未确认**。")
    A("- 「全部校验通过」为文档宣称；本次只读扫描未复跑校验（见附录 B）。")
    A("")
    A("### 3.4 manifest 结构样本（完整 JSON，实测读取）")
    A("")
    A("实验样本 `%s`：" % ap(D["manifest_exp"]["path"]))
    A("")
    A(fence(emb(D["manifest_exp"]["text"]), "json"))
    A("")
    if u01_sample:
        A("教学单元样本 `%s`：" % ap(D["manifest_u01"]["path"]))
        A("")
        A(fence(emb(D["manifest_u01"]["text"]), "json"))
        A("")
    else:
        try:
            k1 = set(json.loads(D["manifest_exp"]["text"]).keys())
            k2 = set(json.loads(D["manifest_u01"]["text"]).keys())
            same = (k1 == k2)
        except Exception:
            same = False
        A("教学单元样本：`%s`（%s；体积纪律不嵌入全文）——实测顶层字段集与 E01 %s（schema=1，experiment=\"U01\"）。" % (
            ap(D["manifest_u01"]["path"]),
            S.fmt_size(os.path.getsize(os.path.join(ROOT, D["manifest_u01"]["path"]))),
            "相同" if same else "不同"))
        A("")
    if D["manifest_proj"]["text"]:
        A("项目样本 `%s`：" % ap(D["manifest_proj"]["path"]))
        A("")
        A(fence(emb(D["manifest_proj"]["text"]), "json"))
    else:
        A("项目（P 系）样本：**无法提供**——本仓不存在 P 系 manifest（实测），外部仓未扫描（任务边界）。")
    A("")
    A("结构解读（扫描员）：schema=1；字段为 `experiment / generated_at / commit / runtime{platform,node,gcc,gdb} / commands[{cmd,exit}] / artifacts[{path,bytes,sha256}] / unverified[]`。这是**实验证据清单**（记录哪条命令在哪个环境跑过、产物哈希、哪些边界未验证），由 `06-实验代码/_template/manifest.mjs` 生成/校验（该文件实测存在：%s）。它**不是** Gemini 建议的「知识点索引 manifest」（无 id/domain/stack/type/difficulty/sandbox_path/related_ids、无笔记元数据、无链接图）。两者用途不同，不能直接复用；但其「生成→校验→防手改」的工具链模式可借鉴。" % ("是" if exists("06-实验代码/_template/manifest.mjs") else "否"))
    A("")

    # ================= 4 README + 总览 =================
    A("## 4. 根文档全文")
    A("")
    readme_b = len(D["readme"].encode("utf-8")) if D["readme"] else 0
    A("### 4.1 `%s`（%s 字节，全文）" % (ap("README.md"), format(readme_b, ",")))
    A("")
    A(fence(emb(D["readme"]), "markdown"))
    A("")
    ov_b = len(D["overview_full"].encode("utf-8")) if D["overview_full"] else 0
    A("### 4.2 `%s`（%s 字节，%d 行 ≤250 行，全文收录）" % (ap("000-学习总览.md"), format(ov_b, ","), D["overview_lines"]))
    A("")
    A(fence(emb(D["overview_full"]), "markdown"))
    A("")

    # ================= 5 Frontmatter =================
    A("## 5. Frontmatter 现状（重点）")
    A("")
    A("### 5.1 全库覆盖率")
    A("")
    A("- 有 frontmatter：**%s** / 无：**%s** / 总 md：**%s** → 覆盖率 **%.1f%%**。" % (
        format(D["fm_yes"], ","), format(D["fm_no"], ","), format(fm_total, ","),
        100.0 * D["fm_yes"] / max(fm_total, 1)))
    A("- 但按一级目录分解后，覆盖率几乎全部由 05 外部镜像贡献：")
    A("")
    A("| 一级目录 | md 数 | 有 fm | 覆盖率 |")
    A("| --- | --- | --- | --- |")
    for k in sorted(D["md_by_dir"]):
        n = len(D["md_by_dir"][k]); y = D["fm_by_top"].get(k, 0)
        A("| %s | %s | %s | %.1f%% |" % (k, format(n, ","), format(y, ","), 100.0 * y / max(n, 1)))
    A("")
    A("**扫描员结论：自有学习笔记的 frontmatter 覆盖率为 0%%**（01/02/06/07 全为 0；08 的 %d 篇有 fm 文件分布为 %s——%s）。Gemini 建议的规范化 YAML frontmatter 在自有笔记侧**完全未落地**。" % (
        own_fm, "、".join("%s %d 篇" % (k, v) for k, v in sorted(fm08_dist.items())),
        "全部位于 RAG-GoldenSet，是判定题的语料数据文件（字段 id/tenant/title/version，服务于多租户检索隔离考题），不是笔记元数据"
        if rag_only else "均为题库数据文件而非学习笔记"))
    A("")
    A("### 5.2 五个重点目录抽样（完整 frontmatter 或「无」）")
    A("")
    for d in S.FOCUS_DIRS:
        yes, no = D["fm_by_dir"][d]
        A("**%s**（有 fm %d / 无 %d）：" % (ap(d), yes, no))
        A("")
        for s in D["fm_samples"][d]:
            A("- 样本 `%s`：" % ap(s["path"]))
            if s["has_fm"]:
                A("")
                A(fence(emb(s["fm"]), "yaml"))
            else:
                t = S.read_text(os.path.join(ROOT, s["path"]))
                first = t.splitlines()[0][:120] if t else "(未读到)"
                A("  **无 frontmatter**（首行即正文：`%s`）" % emb(first))
            A("")
    A("### 5.3 已有字段清单（全库 fm 顶层键，Top %d%s）" % (field_n, "，完整 40 项可由 _lib_scan.py 复现" if field_n < 40 else ""))
    A("")
    A("| 字段 | 出现笔记数 | 主要来源（扫描员判断） |")
    A("| --- | --- | --- |")
    SRC_HINT = {
        "title": "05 抓取内容通用", "category": "05 抓取内容", "url": "05 抓取溯源",
        "scraped_at": "05 抓取时间戳", "doc_updated_at": "05 抓取时间戳", "content_hash": "05 抓取去重",
        "breadcrumb": "05 抓取导航", "id": "05 freeCodeCamp 等 + 08 语料", "challengeType": "05 freeCodeCamp",
        "dashedName": "05 freeCodeCamp", "tags": "05 各来源", "slug": "05 文档站", "page-type": "05 MDN",
        "difficulty": "05 freeCodeCamp/leetcode 类", "browser-compat": "05 MDN", "short-title": "05 MDN",
        "leetcode_no": "05 算法题解", "lang": "05 文档站", "sidebar": "05 文档站", "forumTopicId": "05 freeCodeCamp",
        "tenant": "08 RAG 语料", "version": "08 RAG 语料等",
    }
    for k, n in D["field_ctr"].most_common(field_n):
        A("| %s | %s | %s |" % (k, format(n, ","), SRC_HINT.get(k, "05 外部内容")))
    A("")
    A("任务点名字段实测：tags=%s、aliases=%s、cssclass=%s（后两者全库未出现）。**没有任何自有笔记贡献字段**——上表全部来自 05 外部抓取内容与 08 语料数据。" % (
        format(D["field_ctr"].get("tags", 0), ","), format(D["field_ctr"].get("aliases", 0), ","),
        format(D["field_ctr"].get("cssclass", 0), ",")))
    A("")
    A("Gemini 建议字段全库命中（fm 顶层键精确匹配）：")
    A("")
    A("| 建议字段 | 命中笔记数 |")
    A("| --- | --- |")
    for f in S.GEMINI_FIELDS:
        A("| %s | %s |" % (f, format(D["gemini_ctr"].get(f, 0), ",")))
    A("")
    A("即 `stack / sandbox_path / related_ids` 为 0；`id / difficulty / type / domain` 的命中全部来自外部内容，语义也与 Gemini 方案不同（如 difficulty 是 freeCodeCamp 题目难度，不是笔记学习难度）。")
    A("")

    # ================= 6 链接与组织 =================
    A("## 6. 链接与组织风格")
    A("")
    ls = D["links_scope"]
    A("| 范围 | wikilink `[[...]]` | markdown 链接 `[..](..)`（含图片嵌入） |")
    A("| --- | --- | --- |")
    A("| 全库 | %s | %s |" % (format(D["wiki_n"], ","), format(D["mdlink_n"], ",")))
    A("| 05-外部资料库 | %s | %s |" % (format(ls["wiki_05"], ","), format(ls["md_05"], ",")))
    A("| 自有内容（除 05） | %s | %s |" % (format(ls["wiki_own"], ","), format(ls["md_own"], ",")))
    A("")
    A("解读（扫描员）：外部镜像以 markdown 链接绝对主导（抓取原文如此）；**自有笔记两种风格混用、数量接近**（wiki %d vs md %d），导航层（README/000-学习总览）大量使用 `[[路径|别名]]` wikilink（见第 4 节原文），正文引用外部资料时用 markdown 链接。若 CodeWeave 要解析链接图，需同时支持两种语法；wikilink 目标多为仓库相对路径+别名，无 frontmatter id 可依赖。" % (ls["wiki_own"], ls["md_own"]))
    A("")
    A("目录命名规律（实测归纳）：")
    A("")
    A("- 顶层：两位数字前缀 `01-`…`09-`、`90-`（历史归档），中文语义名。")
    A("- 01-阶段课程：根层 = README + `阶段00`–`阶段10`（11 篇）+ `专项-*`（24 篇，语言/运行时/主题专项）；子目录 `教学单元/U01`–`U09`（字母+数字单元号，各带 evidence/）。根层 md 共 %d 篇。" % len(D["list_01_root"]))
    A("- 02-项目实战：`项目01`–`项目05` + 项目实战总览 + README，共 7 篇：%s。" % "、".join("`%s`" % os.path.basename(p) for p in D["list_02"]))
    A("- 06-实验代码：`E01`–`E13` + `G1`（实验单元）+ `_shared`/`_template`（下划线前缀 = 共享/模板工具）。")
    A("- 08-判定题库：`G0`–`G9`（自学自测包）+ `专题题库`（RAG-GoldenSet/SQL50/全英文面试10套/后端实操30）+ `国内大厂真题`（按公司分目录 + `_工具`）+ evidence。")
    A("- 07-项目实现：仅 README.md（索引），无单元目录。90-历史归档：按日期/来源命名的快照目录。")
    A("- 单元号体系：U（教学）/E（实验）/G（判定包与毕业实验）/P（项目，实现已外迁）/D（深度路线周次）/MS（整合里程碑，见 09-整合任务）。**编号即知识点定位的现成骨架**，但尚未映射到 frontmatter id。")
    A("")
    if D["question_sample"]:
        A("### 6.1 08-判定题库 题型结构样本（前 %d 行%s）" % (q_lines, "，体积纪律由 40 行截断" if q_lines < 40 else ""))
        A("")
        A("`%s`：" % ap(D["question_sample"]["path"]))
        A("")
        A(fence(emb(rehead(D["question_sample"]["head"], q_lines)), "markdown"))
        A("")
    A("结构补充（实测目录树 + check_student_packages.mjs 门禁要求）：每个 G 包 = README + 自评指南 + 参考答案/ + 起始代码/ + 自测脚本/ + 故障变体/ + evidence/（judge-solution.txt、judge-starter.txt）。题型为「函数题 + 仓库题」，判定方式是可执行断言脚本而非人工阅卷；故障变体要求注入受控缺陷验证自测脚本会失败（mutation testing 思路）。")
    A("")

    # ================= 7 scripts 与 CI =================
    A("## 7. scripts/ 目录与 CI 现状")
    A("")
    A("### 7.1 scripts/（3 个文件，无 build-index 类脚本）")
    A("")
    A("| 文件 | 大小 | 用途（据前 30 行实测归纳） |")
    A("| --- | --- | --- |")
    for s in D["scripts"]:
        A("| `%s` | %s | %s |" % (ap("scripts/" + s["name"]), S.fmt_size(s["size"]),
                                   SCRIPT_PURPOSE.get(s["name"], "未确认（未读）")))
    A("")
    A("**`scripts/build-index.js` 不存在**（实测）。相关工具另有两个（实测存在）：`%s`（manifest 生成/校验，被 verify_archive.sh 以 `node ../_template/manifest.mjs verify evidence/manifest.json` 调用）、`%s`（05 目录 source-only 校验，被 verify_all.mjs 调用）。" % (
        ap("06-实验代码/_template/manifest.mjs"), ap("05-外部资料库/tools/catalog_tool.py")))
    A("")
    if script_heads:
        A("各脚本前 30 行原文（证据）：")
        A("")
        for s in D["scripts"]:
            A("`%s`：" % ap("scripts/" + s["name"]))
            A("")
            A(fence(emb(s["head"]), "javascript" if s["name"].endswith(".mjs") else "bash"))
            A("")
    else:
        A("（各脚本前 30 行已实际读取用于判断上表用途；原文因体积纪律不嵌入，可用 `_lib_scan.py` 复现。）")
        A("")
    A("### 7.2 .github/workflows（12 个，全部列出）")
    A("")
    A("| 文件 | 大小 |")
    A("| --- | --- |")
    for w in D["workflows"]:
        A("| `%s` | %s |" % (ap(".github/workflows/" + w["name"]), S.fmt_size(w["size"])))
    A("")
    A("CI 实况（文档宣称，原文见第 4 节 README 与附录 A）：12 个根 workflow **均未在 GitHub Actions 实跑**；2026-11-08 起 Actions 计费阻断，新 run 的 job 不执行（steps=0），annotation 原文 “recent account payments have failed or spending limit needs to be increased”。因此 2026-11-08 之后所有提交都没有云端验证；「全绿」只指本机门禁。本次扫描未查询 GitHub API，run 历史**未确认**。")
    A("")
    for w in D["workflows"]:
        wpath = w["name"] if wf_short else ap(".github/workflows/" + w["name"])
        if w["verify"]:
            A("#### `%s`（全文，%s；完整路径见上表）" % (wpath, S.fmt_size(w["size"])))
            A("")
            A(fence(emb(w["text"]), "yaml"))
        else:
            A("#### `%s`（前 %d 行；完整路径见上表）" % (wpath, wf_lines))
            A("")
            A(fence(emb(rehead(w["text"], wf_lines)), "yaml"))
        A("")
    A("### 7.3 .workbuddy（只记录存在与线索，未读内容）")
    A("")
    A("存在。文件清单（实测）：%s。按目录名与文件命名推断为 AI 工作助手（WorkBuddy）的会话记忆/工作日志（每日一篇 + MEMORY.md 汇总）；`.gitignore` 将其整体排除，注释原文「AI 会话记忆含本机路径与会话元数据，不纳入版本控制」。用途为**推断**，内容未读取（任务要求不 dump）。" % (
        "、".join("`%s`(%s)" % (p, S.fmt_size(s)) for p, s in D["workbuddy_files"])))
    A("")

    # ================= 8 同地性 =================
    A("## 8. 代码与笔记的同地性现状")
    A("")
    A("### 8.1 06-实验代码：同目录自包含（已符合 Colocation 精神）")
    A("")
    A("单元清单（md/代码计数，实测）：")
    A("")
    A("| 单元 | md | 代码 |")
    A("| --- | --- | --- |")
    for sub, m, c in D["colocation"]["06-实验代码"]["units"]:
        A("| %s | %d | %d |" % (sub, m, c))
    A("")
    colo = D["colocation"]["06-实验代码"]
    A("典型单元 `%s` 文件列表（%d 个文件%s；相对 06-实验代码）：" % (
        ap("06-实验代码/" + colo["chosen"]), len(colo["files"]),
        "，采集上限 40，可能截断" if len(colo["files"]) >= 40 else "，完整"))
    A("")
    A("```")
    for f, s in colo["files"][:colo_cap]:
        A("%s  %s" % (f, S.fmt_size(s)))
    if len(colo["files"]) > colo_cap:
        A("…（其余 %d 个略）" % (len(colo["files"]) - colo_cap))
    A("```")
    A("")
    A("解读（扫描员）：每个实验单元 = README.md（笔记/边界）+ src/ + tests/ + scripts/ + evidence/（+ scenarios/ 故障场景笔记），**笔记、代码、证据同目录**，粒度是「实验」而非「知识点」。注意 build/ 下 .exe 为 .gitignore 排除的本地构建产物（源码与 evidence 入库，二进制不入库）。01-阶段课程/教学单元 U01–U09 同构（各带 evidence/manifest.json，代码 %d 个）。" % D["dir_code"].get("01-阶段课程" + SEP + "教学单元", 0))
    A("")
    A("### 8.2 07-项目实现：代码已外迁，本仓纯索引（分离）")
    A("")
    A("实测：07-项目实现 下**无任何子目录**，仅 1 个 README.md（全文如下）。P02/P03/P04 源码在 `E:\\fullstack-code`（存在性已实测；内部布局未确认——07 README 与交接文档用 `projects/` 前缀，而 scripts/verify_archive.sh 用无前缀的 `project02-collab` 等，两处口径不一致，哪个是当前真实布局**未确认**）。项目需求/验收文档在 02-项目实战（7 篇 md、0 代码）。")
    A("")
    p07 = D["p07_readme"]
    p07_n = len(p07.splitlines()) if p07 else 0
    if p07_lines is None or p07_n <= p07_lines:
        A("`%s` 全文（%d 行）：" % (ap("07-项目实现/README.md"), p07_n))
        A("")
        A(fence(emb(p07), "markdown"))
    else:
        A("`%s`（共 %d 行；体积纪律收录前 %d 行，其余截断，全文见该路径）：" % (
            ap("07-项目实现/README.md"), p07_n, p07_lines))
        A("")
        A(fence(emb(rehead(p07, p07_lines)), "markdown"))
    A("")
    A("### 8.3 对 Gemini Colocation 建议的差距判断（扫描员）")
    A("")
    A("- 06/01 已是「单元级同地」，缺的是：知识点级 frontmatter（id/domain/stack/…）、跨单元 related_ids 链接、全局索引。")
    A("- 02（需求）与外部仓（实现）是**跨仓分离**，靠 07 README 的路径表 + sandbox_path 类字段才可能机器可读；当前路径表是给人看的 markdown，且存在 projects/ 前缀口径分歧。")
    A("- 05 外部镜像 13GB 且不入 Git：索引方案必须把它排除或单独分层，否则 manifest 生成与 CodeWeave 拉取都会被拖垮。")
    A("")

    # ================= 9 gitignore =================
    A("## 9. .gitignore 全文与排除分析")
    A("")
    A("`%s`（%s 字节，全文）：" % (ap(".gitignore"), format(len(D["gitignore"].encode("utf-8")) if D["gitignore"] else 0, ",")))
    A("")
    A(fence(emb(D["gitignore"]), "gitignore"))
    A("")
    A("排除分析（扫描员，对照实测工作区）：")
    A("")
    A("- **05-外部资料库/题库/ 与 知识库/ 整体不入 Git**（注释：体积大，用 05-外部资料库/材料清单.md 复现）。即工作区 13GB 镜像的绝大部分是**未跟踪本地文件**；Git 仓库本体远小于工作区（跟踪文件统计见第 1 节）。05 入 Git 的仅 %s 个治理文件（git ls-files 实测：README/catalog.json/catalog.schema.json/tools/catalog_tool.py/材料清单.md 等）。材料清单.md 实测存在：%s；catalog.json（总览宣称的资源事实源）实测存在：%s。复现能力未验证。" % (
        (ts["n05"] if ts else "未确认"),
        "是" if exists("05-外部资料库/材料清单.md") else "否", "是" if exists("05-外部资料库/catalog.json") else "否"))
    A("- `_采集暂存/*` 全部忽略（采集脚本/账本只留本机；工作区可见 %d 个代码文件）。" % D["dir_code"].get("05-外部资料库" + SEP + "_采集暂存", 0))
    A("- `.workbuddy/` 忽略（AI 会话记忆含本机路径，不版本化；git 跟踪数 %s，实测）。" % (ts["wb"] if ts else "未确认"))
    A("- `06-实验代码/**/build/`、`**/node_modules/`、`**/dist/`、`**/*.tsbuildinfo` 忽略：**源码与证据入库，二进制/依赖/构建产物不入库**。E01 的 7 个 .exe、E03/E05 的 dist/ 都是本地产物。")
    A("- `.obsidian/workspace*`、`.obsidian/cache` 忽略（但 .obsidian 目录实测不存在——该库当前可能并未用 Obsidian 打开，或配置在别处；未确认）。")
    A("- 杂项：Thumbs.db、.DS_Store、*.tmp、改名-*.ps1、__pycache__/。")
    A("- **对索引方案的含义**：build-index 若扫描工作区会把 13GB 未跟踪镜像算进去；若只扫 Git 跟踪文件（git ls-files）则天然排除 05 主体，两种口径差异巨大，必须先定口径。")
    A("")

    # ================= 附录 A 交接 =================
    A("## 附录 A. 交接文档（lead 指定收录）")
    A("")
    if D["handover"]:
        hp = D["handover"]["path"]
        full = S.read_text(os.path.join(ROOT, hp))
        nlines = len(full.splitlines()) if full else 0
        A("`%s`（共 %d 行；收录前 %d 行%s）。文档自述为 **2026-11-08 历史快照，不再逐日维护**，其中 HEAD/manifest 数量/CI run 编号是时点值，不可当现状引用；当前口径以 09-整合任务/MS11-状态矩阵 为准（文档自述）。" % (
            ap(hp), nlines, hand_lines, "，即全文" if nlines <= hand_lines else "，已截断"))
        A("")
        A(fence(emb(rehead(D["handover"]["head"], hand_lines)), "markdown"))
    else:
        A("未找到该文件（实测不存在）。")
    A("")

    # ================= 附录 B 未确认 =================
    A("## 附录 B. 未确认清单与口径差异（诚实边界）")
    A("")
    A("1. `E:\\fullstack-code` 内部结构、8 份外部 manifest、P02/P03/P04 源码与测试数字：仅存在性实测，内容**未确认**（任务边界：只负责资料库侧）。")
    A("2. 外部仓项目路径口径：07 README/交接文档用 `projects/project02-collab`，`scripts/verify_archive.sh` 用根级 `project02-collab`——两者不一致，当前真实布局**未确认**。")
    A("3. CI run 历史与计费阻断状态：来自 README/交接文档宣称（原文已嵌入），未查询 GitHub API，**未确认**。")
    A("4. 所有门禁数字（verify_all 21/21、28/28、ARCHIVE VERIFY PASS、各项目测试通过率/覆盖率）：文档宣称，本次**未复跑**（只读纪律；verify_archive.sh 会在临时目录 git init，亦避免执行）。")
    A("5. 05 镜像的「材料清单.md 可复现」能力：未验证（仅确认文件存在性）。")
    A("6. 05 外部内容的质量/版权/时效：未评估（本次只做结构与统计）。")
    A("7. 工作区 vs HEAD 差异：未比对（交接文档警告存在其他会话未提交改动；避免会写 .git/index 的命令）。第 1 节的跟踪文件体积按工作区现状计算，若跟踪文件有未提交修改则与 HEAD 树有出入。")
    A("8. fm 判定把「读取失败」计入无 fm；本次遍历 0 错误，md 读取失败数未单独统计（口径影响极小，如实说明）。")
    A("")
    A("（报告完）")
    return "\n".join(L).replace("{PII_COUNT}", str(len(FLAGS)))


def main():
    D = S.collect()
    report = None
    for trim in range(4):
        FLAGS.clear()
        report = build(D, trim)
        data = report.encode("utf-8")
        print("trim=%d bytes=%d" % (trim, len(data)))
        if len(data) <= LIMIT:
            break
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(report)
    print("WROTE", OUT, len(data), "bytes; trim =", trim)
    print("PII/secret flags:", len(FLAGS), FLAGS[:10])
    # 关键核对数字(供完成消息)
    md_total = len(D["md_files"])
    own_md = sum(len(v) for k, v in D["md_by_dir"].items() if k != "05-外部资料库")
    own_fm = sum(n for k, n in D["fm_by_top"].items() if k != "05-外部资料库")
    print("CHECK md_total=%d fm_yes=%d fm_pct=%.1f own_md=%d own_fm=%d" % (
        md_total, D["fm_yes"], 100.0 * D["fm_yes"] / max(md_total, 1), own_md, own_fm))
    print("CHECK manifests=%d index_jsons=%d workflows=%d build_index=%s" % (
        len(D["manifests"]), len(D["index_jsons"]), len(D["workflows"]), D["build_index_exists"]))
    print("CHECK branch=%s sha=%s fullstack_code=%s walk_errors=%d" % (
        D["branch"], (D["branch_sha"] or "")[:12], D["fullstack_code"], len(D["walk_errors"])))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
