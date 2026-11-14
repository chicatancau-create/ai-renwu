# -*- coding: utf-8 -*-
"""只读扫描 E:\\OBsidian\\全栈工程师学习资料库, 收集快照报告所需全部数据。
绝不写入仓库; 仅读取。stdout 输出紧凑审阅 dump; collect() 供 _lib_report.py 复用。
"""
import os, sys, re, json, subprocess, datetime, collections, fnmatch, stat

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\OBsidian\全栈工程师学习资料库"
EXCLUDE_DIRS = {".git", ".obsidian", "node_modules", "__pycache__"}
CODE_EXTS = {".js",".mjs",".cjs",".ts",".tsx",".jsx",".py",".vue",".java",".go",".rs",
             ".rb",".php",".c",".h",".cpp",".hpp",".cs",".sh",".bat",".cmd",".ps1",
             ".sql",".html",".css",".scss",".less",".swift",".kt",".lua",".r",".pl",".svelte",".astro"}
ATTACH_EXTS = {".png",".jpg",".jpeg",".gif",".webp",".svg",".bmp",".ico",".pdf",".zip",
               ".rar",".7z",".tar",".gz",".mp4",".mp3",".wav",".mov",".doc",".docx",
               ".xls",".xlsx",".ppt",".pptx",".ttf",".woff",".woff2",".eot",".otf"}
FOCUS_DIRS = ["01-阶段课程","02-项目实战","06-实验代码","07-项目实现","08-判定题库"]
GEMINI_FIELDS = ["id","domain","stack","type","difficulty","sandbox_path","related_ids"]

SECRET_PATTERNS = [
    (re.compile(r"://[^/\s:@]+:[^/\s@]+@"), "://***@"),                      # URL 内嵌凭据
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"), "***"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "***"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"), "***"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "***"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"), "***"),
    (re.compile(r"\bglpat-[A-Za-z0-9_\-]{15,}\b"), "***"),
    (re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"), None),  # 仅标记
]
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
CN_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")

def mask(text):
    """脱敏: URL凭据/常见token/邮箱/手机号 → ***; 返回(脱敏后文本, 标记列表)。"""
    flags = []
    if text is None:
        return None, flags
    for pat, repl in SECRET_PATTERNS:
        for m in pat.finditer(text):
            flags.append(("secret-like", m.group(0)[:12] + "..."))
            if repl is not None:
                text = pat.sub(repl, text)
    for m in EMAIL_RE.finditer(text):
        flags.append(("email", m.group(0)))
    text = EMAIL_RE.sub("***@***", text)
    for m in CN_PHONE_RE.finditer(text):
        flags.append(("cn-phone", m.group(0)[:3] + "****"))
    text = CN_PHONE_RE.sub("***", text)
    return text, flags

def read_text(path, limit_bytes=None):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return f.read(limit_bytes) if limit_bytes else f.read()
    except OSError as e:
        return None

def head_lines(text, n, cap=300):
    if text is None:
        return None
    lines = text.splitlines()[:n]
    return "\n".join(l[:cap] for l in lines)

def probe_dir(p):
    """区分 不存在 / 存在 / 无权限 (手册教训: 不能把拒绝读成不存在)。"""
    try:
        st = os.stat(p)
        if stat.S_ISDIR(st.st_mode):
            return "存在(目录)"
        return "存在(非目录)"
    except FileNotFoundError:
        return "不存在"
    except PermissionError:
        return "未确认(权限拒绝,无法判断)"
    except OSError as e:
        return "未确认(%s)" % e

def fm_parse(text):
    """返回 (frontmatter原文 or None, 顶层字段列表)。"""
    if not text:
        return None, []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, []
    for i in range(1, min(len(lines), 200)):
        if lines[i].strip() in ("---", "..."):
            block = lines[1:i]
            keys = []
            for l in block:
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:", l)
                if m:
                    keys.append(m.group(1))
            return "\n".join(block), keys
    return None, []

def collect():
    D = {}
    walk_errors = []
    files = []  # (relpath, size, ext)
    def onerror(e):
        walk_errors.append((getattr(e, "filename", "?"), str(e)))
    for dirpath, dirnames, filenames in os.walk(ROOT, onerror=onerror):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        rel = os.path.relpath(dirpath, ROOT)
        for fn in sorted(filenames):
            fp = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                sz = -1
            ext = os.path.splitext(fn)[1].lower()
            files.append((os.path.join(rel, fn) if rel != "." else fn, sz, ext))
    D["walk_errors"] = walk_errors
    D["files"] = files

    # ---- 全库统计 ----
    ext_hist = collections.Counter()
    total_size = 0
    md_files = []
    for rel, sz, ext in files:
        ext_hist[ext or "(无扩展名)"] += 1
        if sz > 0:
            total_size += sz
        if ext == ".md":
            md_files.append((rel, sz))
    D["total_files"] = len(files)
    D["total_size"] = total_size
    D["ext_hist"] = ext_hist
    D["md_files"] = md_files
    D["code_count"] = sum(n for e, n in ext_hist.items() if e in CODE_EXTS)
    D["attach_count"] = sum(n for e, n in ext_hist.items() if e in ATTACH_EXTS)
    git_size = 0
    for dp, dn, fn in os.walk(os.path.join(ROOT, ".git"), onerror=onerror):
        for f in fn:
            try:
                git_size += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    D["git_size"] = git_size
    D["obsidian_exists"] = os.path.isdir(os.path.join(ROOT, ".obsidian"))

    # ---- 目录计数 (一级/二级) ----
    dir_md = collections.Counter(); dir_code = collections.Counter(); dir_size = collections.Counter()
    for rel, sz, ext in files:
        parts = rel.split(os.sep)
        for depth in (1, 2):
            if len(parts) > depth:
                key = os.sep.join(parts[:depth])
                if ext == ".md":
                    dir_md[key] += 1
                if ext in CODE_EXTS:
                    dir_code[key] += 1
                if sz > 0:
                    dir_size[key] += sz
    D["dir_md"], D["dir_code"], D["dir_size"] = dir_md, dir_code, dir_size

    # ---- 目录树 (深度3, 仅目录) ----
    tree = {}
    for rel, sz, ext in files:
        parts = rel.split(os.sep)
        node = tree
        for p in parts[:-1][:3]:
            node = node.setdefault(p, {})
    D["tree"] = tree
    all_dirs = set()
    for dirpath, dirnames, filenames in os.walk(ROOT, onerror=onerror):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        rel = os.path.relpath(dirpath, ROOT)
        if rel != ".":
            all_dirs.add(rel)
    D["all_dirs"] = all_dirs

    # ---- frontmatter 扫描 + 链接统计 ----
    fm_yes = 0; fm_no = 0
    field_ctr = collections.Counter()
    gemini_ctr = collections.Counter()
    fm_by_dir = {d: [0, 0] for d in FOCUS_DIRS}  # [有, 无]
    fm_by_top = collections.Counter()
    fm_samples = {d: [] for d in FOCUS_DIRS}
    wiki_n = 0; mdlink_n = 0; big_skipped = 0
    wiki_in = wiki_out = md_in = md_out = 0
    md_by_dir = collections.defaultdict(list)
    for rel, sz in md_files:
        top = rel.split(os.sep)[0]
        md_by_dir[top].append(rel)
        text = read_text(os.path.join(ROOT, rel))
        if text is None:
            fm_no += 1
            continue
        fm, keys = fm_parse(text)
        if fm is not None:
            fm_yes += 1
            fm_by_top[top] += 1
            field_ctr.update(keys)
            for k in keys:
                if k in GEMINI_FIELDS:
                    gemini_ctr[k] += 1
            if top in fm_by_dir:
                fm_by_dir[top][0] += 1
                if len([s for s in fm_samples[top] if s["has_fm"]]) < 1:
                    fm_samples[top].append({"path": rel, "has_fm": True, "fm": fm})
        else:
            fm_no += 1
            if top in fm_by_dir:
                fm_by_dir[top][1] += 1
                if len([s for s in fm_samples[top] if not s["has_fm"]]) < 1:
                    fm_samples[top].append({"path": rel, "has_fm": False, "fm": None})
        if sz <= 2 * 1024 * 1024:
            w = len(re.findall(r"\[\[[^\[\]]+?\]\]", text))
            m = len(re.findall(r"\[[^\[\]]*?\]\([^)]*?\)", text))
            wiki_n += w; mdlink_n += m
            if top == "05-外部资料库":
                wiki_in += w; md_in += m
            else:
                wiki_out += w; md_out += m
        else:
            big_skipped += 1
    for d in FOCUS_DIRS:
        if not any(s["has_fm"] for s in fm_samples[d]):
            for rel in sorted(md_by_dir.get(d, [])):
                if os.path.basename(rel).lower() != "readme.md" and not any(s["path"] == rel for s in fm_samples[d]):
                    t2 = read_text(os.path.join(ROOT, rel))
                    fm2, _ = fm_parse(t2)
                    fm_samples[d].append({"path": rel, "has_fm": fm2 is not None, "fm": fm2})
                    break
    D["fm_by_top"] = fm_by_top
    D["links_scope"] = {"wiki_05": wiki_in, "md_05": md_in, "wiki_own": wiki_out, "md_own": md_out}
    D["fm_yes"], D["fm_no"] = fm_yes, fm_no
    D["field_ctr"], D["gemini_ctr"] = field_ctr, gemini_ctr
    D["fm_by_dir"], D["fm_samples"] = fm_by_dir, fm_samples
    D["wiki_n"], D["mdlink_n"], D["big_skipped"] = wiki_n, mdlink_n, big_skipped
    D["md_by_dir"] = dict(md_by_dir)

    # ---- 索引文件 ----
    manifests, index_jsons = [], []
    for rel, sz, ext in files:
        base = os.path.basename(rel).lower()
        if ext == ".json" and "manifest" in base:
            manifests.append((rel, sz))
        elif ext == ".json" and "index" in base:
            index_jsons.append((rel, sz))
    D["manifests"] = sorted(manifests)
    D["index_jsons"] = sorted(index_jsons)
    def pick(pred):
        for rel, sz in sorted(manifests):
            if pred(rel):
                return rel
        return None
    exp = pick(lambda r: r.startswith("06-实验代码" + os.sep + "E01"))
    u01 = pick(lambda r: "U01-" in r)
    proj = pick(lambda r: re.search(r"[\\/]P0\d", r))
    D["manifest_exp"] = {"path": exp, "text": read_text(os.path.join(ROOT, exp)) if exp else None}
    D["manifest_u01"] = {"path": u01, "text": read_text(os.path.join(ROOT, u01)) if u01 else None}
    D["manifest_proj"] = {"path": proj, "text": read_text(os.path.join(ROOT, proj)) if proj else None}
    D["index_samples"] = [{"path": p, "head": head_lines(read_text(os.path.join(ROOT, p)), 30)}
                          for p, _ in sorted(index_jsons)[:3]]

    # ---- scripts/ ----
    scripts = []
    sdir = os.path.join(ROOT, "scripts")
    if os.path.isdir(sdir):
        for fn in sorted(os.listdir(sdir)):
            fp = os.path.join(sdir, fn)
            if os.path.isfile(fp):
                scripts.append({"name": fn, "size": os.path.getsize(fp),
                                "head": head_lines(read_text(fp), 30)})
    D["scripts"] = scripts
    D["build_index_exists"] = os.path.isfile(os.path.join(sdir, "build-index.js"))

    # ---- .github / .workbuddy ----
    gh = []
    for dp, dn, fn in os.walk(os.path.join(ROOT, ".github"), onerror=onerror):
        dn[:] = sorted(dn)
        for f in sorted(fn):
            fp = os.path.join(dp, f)
            gh.append((os.path.relpath(fp, ROOT), os.path.getsize(fp)))
    D["github_files"] = gh
    wfs = []
    wfdir = os.path.join(ROOT, ".github", "workflows")
    if os.path.isdir(wfdir):
        for fn in sorted(os.listdir(wfdir)):
            fp = os.path.join(wfdir, fn)
            if os.path.isfile(fp):
                text = read_text(fp)
                is_verify = "verify-all" in fn.lower()
                wfs.append({"name": fn, "size": os.path.getsize(fp), "verify": is_verify,
                            "text": text if is_verify else head_lines(text, 25)})
    D["workflows"] = wfs
    wb = []
    wbdir = os.path.join(ROOT, ".workbuddy")
    if os.path.isdir(wbdir):
        for dp, dn, fn in os.walk(wbdir, onerror=onerror):
            dn[:] = sorted(dn)
            for f in sorted(fn):
                fp = os.path.join(dp, f)
                wb.append((os.path.relpath(fp, ROOT), os.path.getsize(fp)))
    D["workbuddy_files"] = wb

    # ---- 06/07 同地性 ----
    colo = {}
    for d in ("06-实验代码", "07-项目实现"):
        base = os.path.join(ROOT, d)
        units = []
        if os.path.isdir(base):
            for sub in sorted(os.listdir(base)):
                sp = os.path.join(base, sub)
                if os.path.isdir(sp):
                    m = sum(1 for r, _, _ in files if r.startswith(d + os.sep + sub + os.sep) and r.endswith(".md"))
                    c = sum(1 for r, _, e in files if r.startswith(d + os.sep + sub + os.sep) and e in CODE_EXTS)
                    units.append((sub, m, c))
        chosen = None
        for sub, m, c in units:
            if m > 0 and c > 0:
                chosen = sub; break
        if chosen is None and units:
            chosen = units[0][0]
        flist = []
        if chosen:
            cp = os.path.join(base, chosen)
            for dp, dn, fn in os.walk(cp, onerror=onerror):
                dn[:] = sorted(x for x in dn if x not in EXCLUDE_DIRS)
                for f in sorted(fn):
                    fp = os.path.join(dp, f)
                    flist.append((os.path.relpath(fp, base), os.path.getsize(fp)))
                    if len(flist) >= 40:
                        break
                if len(flist) >= 40:
                    break
        colo[d] = {"units": units, "chosen": chosen, "files": flist}
    D["colocation"] = colo

    # ---- 08 题型样本 ----
    qsample = None
    qdir = os.path.join(ROOT, "08-判定题库")
    if os.path.isdir(qdir):
        cands = sorted(r for r in md_by_dir.get("08-判定题库", [])
                       if not re.search(r"(README|索引|总览|说明)", os.path.basename(r), re.I))
        if cands:
            qsample = {"path": cands[0], "head": head_lines(read_text(os.path.join(ROOT, cands[0])), 40)}
    D["question_sample"] = qsample

    # ---- 根文档 / 交接 ----
    D["readme"] = read_text(os.path.join(ROOT, "README.md"))
    D["p07_readme"] = read_text(os.path.join(ROOT, "07-项目实现", "README.md"))
    D["list_02"] = sorted(md_by_dir.get("02-项目实战", []))
    D["list_07"] = sorted(md_by_dir.get("07-项目实现", []))
    D["list_01_root"] = sorted(r for r in md_by_dir.get("01-阶段课程", []) if r.count(os.sep) == 1)
    ov = read_text(os.path.join(ROOT, "000-学习总览.md"))
    D["overview_full"] = ov
    D["overview_lines"] = len(ov.splitlines()) if ov else 0
    D["gitignore"] = read_text(os.path.join(ROOT, ".gitignore"))
    hand_p = os.path.join(ROOT, "04-资源与评估", "交接-下一个AI-2026-11-08.md")
    D["handover"] = {"path": os.path.relpath(hand_p, ROOT),
                     "head": head_lines(read_text(hand_p), 120)} if os.path.isfile(hand_p) else None

    # ---- git ----
    head = read_text(os.path.join(ROOT, ".git", "HEAD")) or ""
    branch = head.strip().replace("ref: refs/heads/", "") if head.startswith("ref:") else "(detached)"
    D["branch"] = branch
    refp = os.path.join(ROOT, ".git", "refs", "heads", *branch.split("/"))
    D["branch_sha"] = (read_text(refp) or "").strip() or None
    cfg = read_text(os.path.join(ROOT, ".git", "config")) or ""
    D["git_remotes"] = re.findall(r'\[remote "([^"]+)"\]\s*\n\s*url = (.+)', cfg)
    D["git_proxy"] = re.findall(r'\[http "([^"]+)"\]\s*\n\s*proxy = (.+)', cfg)
    commits = None; src = "git log"
    try:
        r = subprocess.run(["git", "-C", ROOT, "log", "-3", "--date=iso-strict",
                            "--pretty=format:%h|%ad|%s"],
                           capture_output=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            commits = [l.split("|", 2) for l in r.stdout.strip().splitlines()]
    except (OSError, subprocess.TimeoutExpired):
        pass
    if commits is None:
        src = "未确认(git log 不可用)"
        logp = os.path.join(ROOT, ".git", "logs", "HEAD")
        txt = read_text(logp)
        if txt:
            rows = []
            for l in txt.splitlines():
                m = re.match(r"^([0-9a-f]{40}) ([0-9a-f]{40}) .+? (\d+) [+\-]\d+\tcommit(?: \([^)]*\))?: (.*)$", l)
                if m:
                    ts = datetime.datetime.fromtimestamp(int(m.group(3))).strftime("%Y-%m-%d %H:%M:%S")
                    rows.append([m.group(2)[:7], ts + " (本地reflog时间)", m.group(4)])
            if rows:
                commits = rows[-3:][::-1]
                src = ".git/logs/HEAD reflog 回退解析"
    D["commits"], D["commits_src"] = commits, src
    D["fullstack_code"] = probe_dir(r"E:\fullstack-code")
    return D

def fmt_size(n):
    if n is None or n < 0:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f%s" % (n, unit) if unit != "B" else "%dB" % n
        n /= 1024.0

def dump(D):
    P = print
    P("=== 1 GIT ===")
    P("branch:", D["branch"], "sha:", D["branch_sha"])
    P("remotes:", D["git_remotes"], "proxy:", D["git_proxy"])
    P("commits(%s):" % D["commits_src"], D["commits"])
    P("E:\\fullstack-code:", D["fullstack_code"])
    P("walk_errors:", D["walk_errors"][:10], "共", len(D["walk_errors"]))
    P(".obsidian exists:", D["obsidian_exists"])
    P("=== 2 TREE (depth3, md/code 计数) ===")
    def show(node, prefix, depth):
        items = sorted(node.items())
        for i, (name, sub) in enumerate(items):
            if i >= 40:
                P(prefix + "... 另有 %d 个目录未展开" % (len(items) - 40)); break
            rel = (prefix_rel[0] + "/" + name) if prefix_rel[0] else name
            ann = ""
            if depth <= 2:
                key = rel.replace("/", os.sep)
                ann = "  [md:%d code:%d]" % (D["dir_md"].get(key, 0), D["dir_code"].get(key, 0))
            P(prefix + name + "/" + ann)
            if depth < 3:
                old = prefix_rel[0]
                prefix_rel[0] = rel
                show(sub, prefix + "  ", depth + 1)
                prefix_rel[0] = old
    prefix_rel = [""]
    show(D["tree"], "", 1)
    P("=== 3 STATS ===")
    P("files:", D["total_files"], "size:", fmt_size(D["total_size"]), ".git:", fmt_size(D["git_size"]))
    P("md:", len(D["md_files"]), "code:", D["code_count"], "attach:", D["attach_count"])
    P("ext_hist:", D["ext_hist"].most_common(40))
    P("manifests(%d):" % len(D["manifests"]))
    for p, s in D["manifests"]:
        P("  ", p, fmt_size(s))
    P("index_jsons(%d):" % len(D["index_jsons"]), [p for p, _ in D["index_jsons"]][:20])
    P("=== 5 FRONTMATTER ===")
    tot = D["fm_yes"] + D["fm_no"]
    P("有fm: %d / 无fm: %d / 总: %d (%.1f%%)" % (D["fm_yes"], D["fm_no"], tot, 100.0 * D["fm_yes"] / max(tot, 1)))
    P("fm_by_top:", D["fm_by_top"].most_common())
    P("md_by_top:", {k: len(v) for k, v in sorted(D["md_by_dir"].items())})
    P("size_by_top:", {k: fmt_size(v) for k, v in sorted(D["dir_size"].items()) if os.sep not in k})
    P("fields:", D["field_ctr"].most_common(40))
    P("gemini_fields:", dict(D["gemini_ctr"]))
    P("by_dir:", D["fm_by_dir"])
    for d, ss in D["fm_samples"].items():
        for s in ss:
            P("--- sample:", s["path"], "has_fm:", s["has_fm"])
            if s["fm"]:
                P(s["fm"][:800])
    P("=== 6 LINKS ===")
    P("wikilinks:", D["wiki_n"], "mdlinks:", D["mdlink_n"], "big_skipped:", D["big_skipped"])
    P("links_scope:", D["links_scope"])
    P("=== MANIFEST SAMPLES ===")
    for k in ("manifest_exp", "manifest_u01", "manifest_proj"):
        P("---", k, D[k]["path"])
        if D[k]["text"]:
            P(D[k]["text"][:4000])
    P("=== 07 README ===")
    P(head_lines(D["p07_readme"], 60))
    P("list_02:", D["list_02"])
    P("list_07:", D["list_07"])
    P("list_01_root:", D["list_01_root"])
    if D["question_sample"]:
        P("--- 08 sample:", D["question_sample"]["path"])
        P(D["question_sample"]["head"])
    P("=== 7 SCRIPTS ===")
    P("build-index.js exists:", D["build_index_exists"])
    for s in D["scripts"]:
        P("--- scripts/%s (%s)" % (s["name"], fmt_size(s["size"])))
        P(s["head"])
    P("github_files:", D["github_files"])
    P("workflows:", [(w["name"], w["size"], w["verify"]) for w in D["workflows"]])
    P("workbuddy_files:", D["workbuddy_files"])
    P("=== 8 COLOCATION ===")
    for d, c in D["colocation"].items():
        P(d, "units:", c["units"][:25], "chosen:", c["chosen"])
        for f, s in c["files"]:
            P("   ", f, fmt_size(s))
    P("=== 4 DOCS ===")
    P("readme bytes:", len(D["readme"].encode("utf-8")) if D["readme"] else None,
      "overview lines:", D["overview_lines"], "gitignore bytes:", len(D["gitignore"].encode("utf-8")) if D["gitignore"] else None)
    P("handover:", D["handover"]["path"] if D["handover"] else "不存在")
    P("=== PII FLAGS (embeds) ===")
    for key in ("readme", "overview_full", "gitignore"):
        _, fl = mask(D[key])
        if fl:
            P(key, fl[:20])
    for w in D["workflows"]:
        _, fl = mask(w["text"])
        if fl:
            P("wf:" + w["name"], fl[:10])
    for s in D["scripts"]:
        _, fl = mask(s["head"])
        if fl:
            P("script:" + s["name"], fl[:10])
    if D["handover"]:
        _, fl = mask(D["handover"]["head"])
        if fl:
            P("handover", fl[:20])
    for k in ("manifest_exp", "manifest_proj"):
        _, fl = mask(D[k]["text"])
        if fl:
            P(k, fl[:10])

if __name__ == "__main__":
    try:
        D = collect()
        dump(D)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
