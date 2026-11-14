# -*- coding: utf-8 -*-
# 只读组装 G:\AIrenwu\02_项目代码\gemini-pack\01-CodeWeave-快照.md
# 所有嵌入内容均从 G:\CodeWeave 磁盘真实读取；本脚本不写入 CodeWeave 任何文件。
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"G:\CodeWeave"
OUT = r"G:\AIrenwu\02_项目代码\gemini-pack\01-CodeWeave-快照.md"
BUDGET = 69500  # 字节，任务上限 70KB，留余量

EXCLUDE = {"node_modules", ".git", "dist", "build", "out", ".next", "coverage", "__pycache__", ".venv", ".gradle"}
PRIVACY = {".local", ".claude", "工作区"}
MAXDEPTH = 3

# ---------- 目录树（与 _cw_tree.py 同参数） ----------
def walk_dirs(d):
    for base, dirs, files in os.walk(d):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDE and x not in PRIVACY)
        yield base, dirs, files

def count_files(d):
    return sum(len(f) for _, _, f in walk_dirs(d))

tree_lines = []
def tree(d, depth):
    try:
        entries = list(os.scandir(d))
    except OSError as e:
        tree_lines.append("    " * depth + "[读取失败: %s]" % e)
        return
    entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
    dirs = [e for e in entries if e.is_dir() and e.name not in EXCLUDE]
    files = [e for e in entries if not e.is_dir() and e.name not in EXCLUDE]
    for e in dirs:
        ind = "    " * depth
        if e.name in PRIVACY:
            tree_lines.append("%s%s/  [隐私目录,不展开;内含约%d个文件]" % (ind, e.name, count_files(e.path)))
            continue
        tree_lines.append("%s%s/  (%d 文件)" % (ind, e.name, count_files(e.path)))
        if depth + 1 < MAXDEPTH:
            tree(e.path, depth + 1)
    shown = files if len(files) <= 15 else files[:5]
    for e in shown:
        ind = "    " * depth
        try:
            sz = e.stat().st_size
        except OSError:
            sz = -1
        tree_lines.append("%s%s  (%dB)" % (ind, e.name, sz))
    if len(files) > 15:
        tree_lines.append("%s…(其余 %d 个文件略)" % ("    " * depth, len(files) - 5))

tree(ROOT, 0)
TREE = "\n".join(tree_lines)

# ---------- 文件读取/嵌入 ----------
def rd(rel):
    p = os.path.join(ROOT, rel)
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()

def lines_of(rel):
    t = rd(rel)
    ls = t.split("\n")
    if ls and ls[-1] == "":
        ls.pop()
    return ls

def sz(rel):
    return os.path.getsize(os.path.join(ROOT, rel))

def find_line(rel, needle):
    for i, ln in enumerate(lines_of(rel), 1):
        if needle in ln:
            return i
    return None

def ref(rel, needle):
    n = find_line(rel, needle)
    return "G:\\CodeWeave\\%s:%s" % (rel, n if n else "行号未确认")

LANG = {".json": "json", ".ts": "ts", ".tsx": "tsx", ".mjs": "js", ".js": "js",
        ".cpp": "cpp", ".hpp": "cpp", ".kt": "kotlin", ".kts": "kotlin",
        ".yaml": "yaml", ".md": "markdown", ".html": "html", ".xml": "xml",
        ".tsv": "text", ".txt": "text", ".yaml": "yaml", ".properties": "properties"}

def lang_of(rel):
    return LANG.get(os.path.splitext(rel)[1].lower(), "text")

def embed(rel, a=None, b=None, numbered=False, note=None):
    r"""嵌入 G:\CodeWeave\<rel>；a/b 为 1 基行号闭区间；numbered=True 时带行号。"""
    ls = lines_of(rel)
    total = len(ls)
    full = a is None
    seg = ls if full else ls[a - 1:b]
    head = "G:\\CodeWeave\\%s" % rel
    if full:
        head += "（全文 %d 行，%d 字节）" % (total, sz(rel))
    else:
        head += "（第 %d–%d 行 / 共 %d 行，%d 字节%s）" % (a, min(b, total), total, sz(rel), "，截断" if b < total else "")
    if note:
        head += "　" + note
    body = "\n".join(("%d: %s" % (a + i, ln)) if numbered else ln for i, ln in enumerate(seg)) if not full else "\n".join(
        ("%d: %s" % (i + 1, ln)) if numbered else ln for i, ln in enumerate(seg))
    return "#### " + head + "\n\n````" + lang_of(rel) + "\n" + body + "\n````\n"

# ---------- README 发现与分类 ----------
KNOWN_READMES = [
    ("应用端\\项目\\README.md", None),
    ("应用端\\项目\\native\\README.md", None),
    ("应用端\\项目\\cert\\README.md", "cert"),
    ("移动端\\项目\\README.md", None),
    ("网页端\\项目\\README.md", None),
    ("网页端\\项目\\server\\README.md", None),
    ("网页端\\项目\\deploy\\README.md", None),
    ("网页端\\项目\\src\\content\\README-attachments.md", "attach"),
    ("网页端\\项目\\src\\design\\README.md", "design"),
]
known_set = {r for r, _ in KNOWN_READMES}
all_readmes, evidence_readmes, sdk_readmes, flagged = [], [], [], []
for base, dirs, files in walk_dirs(ROOT):
    for f in files:
        if f.lower().startswith("readme") and f.lower().endswith(".md"):
            rel = os.path.relpath(os.path.join(base, f), ROOT)
            all_readmes.append(rel)
            if rel in known_set:
                continue
            if "\\开发环境\\" in rel:
                sdk_readmes.append(rel)
            elif "\\验收证据\\" in rel:
                evidence_readmes.append(rel)
            else:
                flagged.append(rel)
evidence_readmes.sort()

# ---------- 统计 ----------
top_counts = {}
for e in sorted(os.scandir(ROOT), key=lambda x: x.name):
    if e.is_dir() and e.name not in EXCLUDE and e.name not in PRIVACY:
        top_counts[e.name] = count_files(e.path)
total_files = sum(len(f) for _, _, f in walk_dirs(ROOT))
privacy_counts = {n: count_files(os.path.join(ROOT, n)) for n in sorted(PRIVACY) if os.path.isdir(os.path.join(ROOT, n))}

catalog_lines = [ln for ln in lines_of("应用端\\项目\\native\\content\\catalog.v1.tsv") if ln.strip()]
def hexdec(h):
    try:
        return bytes.fromhex(h).decode("utf-8")
    except Exception:
        return "?"
cat_first = catalog_lines[0].split("\t") if catalog_lines else []
cat_decoded = " / ".join(hexdec(x) for x in cat_first[:4]) if cat_first else ""

# ---------- 技术栈证据行 ----------
W = "网页端\\项目\\package.json"
A = "应用端\\项目\\package.json"
M = "移动端\\项目\\build.gradle.kts"
MA = "移动端\\项目\\mobile-app\\build.gradle.kts"
EV = {
    "react": ref(W, '"react"'), "vite": ref(W, '"vite"'), "ts": ref(W, '"typescript"'),
    "vitest": ref(W, '"vitest"'), "appdesc": ref(A, '"description"'),
    "agp": ref(M, "com.android.application"), "kotlin": ref(M, "kotlin"),
    "compilesdk": ref(MA, "compileSdk"), "material3": ref(MA, "material3"),
    "cxx23": ref("应用端\\项目\\native\\CMakeLists.txt", "CMAKE_CXX_STANDARD 23"),
    "entry": ref("网页端\\项目\\index.html", "src/main.tsx"),
}

GITIGNORE_KEYS = ["node_modules", ".env", "*.local", "pfx", "p12", "*.key", "工作区", ".claude", ".local",
                  "开发环境", "构建产物", "启动", "server/data", "workspace", ".apk", ".exe", ".gradle"]
def gitignore_excerpt(cap=22):
    out, seen = [], set()
    for i, ln in enumerate(lines_of(".gitignore"), 1):
        if any(k in ln for k in GITIGNORE_KEYS) and i not in seen:
            out.append("%d: %s" % (i, ln)); seen.add(i)
        if len(out) >= cap:
            break
    return "\n".join(out)

VITE_KEYS = ["defineConfig", "resolveApiOrigin", "plugins:", "react()", "base:", "minify",
             "manualChunks", "icons", "react-vendor", "port: 5173", "proxy:", "'/api'",
             "target:", "changeOrigin", "preview:", "port: 4173", "host:", "strictPort"]
def vite_excerpt():
    out = []
    for i, ln in enumerate(lines_of("网页端\\项目\\vite.config.ts"), 1):
        if any(k in ln for k in VITE_KEYS):
            out.append("%d: %s" % (i, ln))
    return "\n".join(out)

# ---------- 报告组装 ----------
def build(L):
    S = []
    add = S.append

    add("# CodeWeave 仓库快照报告（供 Gemini 架构分析）\n")
    add("- 扫描时间：2026-11-12；扫描者：codeweave-scan（只读子代理）；对象：`G:\\CodeWeave`（只读，未修改任何文件、未执行任何改变 git 状态的命令）。")
    add("- 用途：为「fullstack-study-library（Obsidian 资料库）输出 manifest.json 数据契约供 CodeWeave 消费」的方案提供 CodeWeave 一侧的真实结构、配置与代码事实。")
    add("- 方法：read/glob/grep 工具真实读取 + 只读 Python 脚本生成目录树与统计；本报告嵌入的文件内容全部由脚本直接从磁盘读取原文。读不到/判不了的一律标注「未确认」。")
    add("- 脱敏与隐私：git 远端 URL 经检查不含内嵌 token/密码；`.local/`、`.claude/`、`工作区/` 只记录存在与用途线索，不 dump 内容；签名私钥类文件（*.pfx）只记录存在。")
    add("- 体积纪律：总量 ≤70KB。验收证据类 README（38 个）不内联（只列清单/计数），超长 README 与低优先级配置按预算截断/节选（截断处均注明）——此为预算取舍，非遗漏。\n")

    # ===== 1 概览 =====
    add("## 1. 仓库概览\n")
    add("### 1.1 Git 状态（实测）\n")
    add("````text\nremote origin   https://github.com/chicatancau-create/CodeWeave.git\nremote gitcode  https://gitcode.com/zhoumoyukuai/CodeWeave.git\n当前分支        codex/project-layout-20261106   （读 .git/HEAD）\n最近 3 条提交（git -C G:\\CodeWeave log -3 --format=\"%h %ad %s\" --date=short）：\n396d3fa 2026-11-12 修正窄窗布局并校准验收口径\n574958f 2026-11-11 修复顶栏浮层动效并补充拆分对照证据\n1ef6455 2026-11-11 docs: 本轮修缮验收记录与进度同步\n````\n")
    add("两个远端 URL 均无内嵌凭据，无需脱敏。\n")
    add("### 1.2 顶层目录用途（基于实际内容判断）\n")
    add("| 目录/文件 | 实测文件数* | 用途 |")
    add("|---|---|---|")
    add("| `应用端/` | %d | C++23 桌面端：`项目/`=源码（native Win32 壳 + 可选 Qt6 QML 壳 + 只读内容源），`开发环境/`=Qt 6.8.3 msvc2022_64 SDK 与签名材料，`构建产物/qt/current/`=唯一当前构建，`工程文件/`=验收证据与工程文档 |" % top_counts.get("应用端", -1))
    add("| `网页端/` | %d | React/Vite 网页客户端 + 零依赖纯 Node 网页服务（`项目/server/`），含 OpenAPI 契约与内容编译管线 |" % top_counts.get("网页端", -1))
    add("| `移动端/` | %d | Android/Kotlin Jetpack Compose 骨架（`mobile-app/`）+ C++20 共享核心（`mobile-core/`，独立 CMake，不在 Gradle 内） |" % top_counts.get("移动端", -1))
    add("| `工程文件/` | %d | 仓库级工程文档（项目结构索引/基线/终验报告）与工具（check-layout.mjs、初始化本机入口.ps1、构建当前Qt.cmd 等） |" % top_counts.get("工程文件", -1))
    add("| `工作区/` | %d（不展开） | 桌面端配置与真实运行数据（项目基线-第一版.md:14），含账户/草稿/学习记录等隐私（AGENTS.md 明令不上传），本次只记录存在 |" % privacy_counts.get("工作区", -1))
    add("| `.local/` | 约 %d（不展开） | Qt 构建用英文 junction：app→应用端/项目、prep→应用端/开发环境/CodeWeave-prep、qt→应用端/构建产物/qt（check-layout.mjs 断言）；内容与目标目录重复，不单独计数 |" % privacy_counts.get(".local", -1))
    add("| `.claude/` | %d（不展开） | 内容未读取；用途未确认（按名称推测为 Claude Code 本地配置，仅推测） |" % privacy_counts.get(".claude", -1))
    add("| `.git/` | — | git 元数据，排除扫描 |")
    add("| 根文件 | — | `AGENTS.md`（目录规则，见 §3）、`.gitignore`（隐私/产物排除，见 §5）、`.gitattributes`（native/content 字节保真，见 §5）。**根目录无 README、无 package.json** |")
    add("")
    add("\\* 文件数排除 node_modules/.git/dist/build/out/.next/coverage/__pycache__/.venv/.gradle 与隐私目录；总计 %d。三端源码都在各端 `项目/` 子目录内（外层仅一个启动 .lnk + 工程文件/）。" % total_files)
    add("")
    add("历史沿革：`工程文件/项目基线-第一版.md`（2026-10-04）记载应用端最初为「Windows Electron 应用端和 C++ 原生重构入口」，现已原生化（A2数据兼容契约.md:5「旧 Electron 字段仅作为显式导入来源」）；该文档提到的 `备份区/` 在当前顶层不存在（去向未确认）。当前权威目录规则以 AGENTS.md（2026-11-06）与 工程文件/项目结构索引.md 为准。\n")

    # ===== 2 目录树 =====
    add("## 2. 目录树（深度 3，脚本生成）\n")
    add("排除：node_modules、.git、dist、build、out、.next、coverage、__pycache__、.venv、.gradle；隐私目录（.local/.claude/工作区）只计数不展开；单目录超过 15 个文件时只显示前 5 个并计数。每个目录后括注其递归文件数（同口径排除）。\n")
    add("````text\n" + TREE + "\n````\n")

    # ===== 3 规则文件 =====
    add("## 3. 仓库规则与结构文档（全文）\n")
    add(embed("AGENTS.md"))
    add(embed("工程文件\\项目结构索引.md"))
    add(embed("工程文件\\工具\\check-layout.mjs", 1, 30, note="lead 指定收前 30 行；检查项：根目录白名单、每端外层恰好 1 个 lnk+项目/+工程文件/、禁旧路径、.local 三 junction realpath 相等、AGENTS.md 关键句、构建产物/qt 下只许 current"))
    if L["codestruct"]:
        add(embed("应用端\\工程文件\\代码结构.md"))

    # ===== 4 README =====
    add("## 4. README 收录\n")
    add("全仓共发现 %d 个 README（排除 node_modules 等）：9 个项目 README（全文或按预算截断，截断处均注明）+ %d 个验收证据 README（只列清单/计数不内联——70KB 预算取舍，内容多为截图与验收记录而非架构）。开发环境（Qt SDK）内未发现 README。" % (len(all_readmes), len(evidence_readmes)))
    if flagged:
        add("未归类 README（需人工复核）：" + "；".join(flagged))
    add("")
    for rel, kind in KNOWN_READMES:
        if kind == "attach":
            add(embed(rel, 1, L["attach"]))
        elif kind == "design":
            add(embed(rel, 1, L["design"]))
        elif rel == "网页端\\项目\\README.md" and L["webreadme"]:
            add(embed(rel, 1, L["webreadme"]))
        elif kind == "cert" and L["certreadme"]:
            add(embed(rel, 1, L["certreadme"]))
        else:
            add(embed(rel))
    add("### 4.1 验收证据 README 清单（不内联）\n")
    if L["evidence"] == "list":
        for rel in evidence_readmes:
            add("- `G:\\CodeWeave\\%s`（%d 字节）" % (rel, sz(rel)))
    else:
        add("共 %d 个，位于 应用端/工程文件/验收证据/ 与 网页端/工程文件/验收证据/ 各 Phase/阶段子目录内（完整路径见 §2 目录树），总计 %d 字节。" % (len(evidence_readmes), sum(sz(r) for r in evidence_readmes)))
    add("")

    # ===== 5 核心配置 =====
    add("## 5. 核心配置（全文，低优先级项截断）\n")
    add("**Workspace 结构说明：不是 monorepo。** 根目录无 package.json；`应用端/项目/pnpm-workspace.yaml` 仅一行注释、无 packages 声明；三端各自独立管理依赖，网页服务是网页端内的嵌套包（server/package.json，零依赖）。\n")
    add("### 5.1 package.json（三端）\n")
    add(embed("应用端\\项目\\package.json"))
    add(embed("网页端\\项目\\package.json"))
    add(embed("网页端\\项目\\server\\package.json"))
    add(embed("应用端\\项目\\pnpm-workspace.yaml"))
    add("### 5.2 构建配置\n")
    if L["vite"] == "full":
        add(embed("网页端\\项目\\vite.config.ts"))
    else:
        add("#### G:\\CodeWeave\\网页端\\项目\\vite.config.ts（关键行节选，带原行号 / 共 %d 行，%d 字节；完整原文未内联——预算取舍）\n\n````ts\n%s\n````\n" % (len(lines_of("网页端\\项目\\vite.config.ts")), sz("网页端\\项目\\vite.config.ts"), vite_excerpt()))
    if L["nativecmake"]:
        add(embed("应用端\\项目\\native\\CMakeLists.txt", 1, L["nativecmake"]))
        add("（后续未内联部分：codeweave-core 源文件清单、codeweave-native WIN32 可执行目标 :23、/utf-8 编译选项 :20,30、CTest 四个测试 native-core/native-content-delivery/native-startup --self-test/gui-smoke :50–61、ui-qt 子目录 :87–89。）")
    else:
        add(embed("应用端\\项目\\native\\CMakeLists.txt"))
    add(embed("应用端\\项目\\native\\ui-qt\\CMakeLists.txt", 1, L["uiqt"]))
    add(embed("移动端\\项目\\build.gradle.kts"))
    if L["settingsgradle"]:
        add(embed("移动端\\项目\\settings.gradle.kts"))
    else:
        add("settings.gradle.kts（4 行，未内联）：rootProject.name=\"codeweave-mobile\"；include(\":mobile-app\")（mobile-core 不在 Gradle 内，独立 CMake）。")
    if L["gradleprops"]:
        add(embed("移动端\\项目\\gradle.properties"))
    else:
        add("gradle.properties（3 行，未内联）：org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8；android.useAndroidX=true。")
    add(embed("移动端\\项目\\mobile-app\\build.gradle.kts"))
    add(embed("移动端\\项目\\mobile-core\\CMakeLists.txt"))
    add("### 5.3 tsconfig（网页端）\n")
    add(embed("网页端\\项目\\tsconfig.json"))
    add(embed("网页端\\项目\\tsconfig.app.json"))
    if L["tsconfignode"]:
        add(embed("网页端\\项目\\tsconfig.node.json"))
    else:
        add("tsconfig.node.json（16 行，未内联）：ES2023、allowImportingTsExtensions、verbatimModuleSyntax、noEmit，include 仅 vite.config.ts。")
    add("### 5.4 运行时配置与环境\n")
    add(embed("应用端\\项目\\config\\codeweave.config.example.json"))
    add(embed("网页端\\项目\\server\\config\\codeweave.config.example.json"))
    add(embed("网页端\\项目\\.env.local", note="唯一 env 文件；值为本机开发 API origin（localhost），非凭据，无需脱敏。仓库内未发现 .env.example"))
    add(embed("网页端\\项目\\.nvmrc"))
    add("### 5.5 仓库级忽略与属性\n")
    add(embed(".gitattributes"))
    if L["gitignore"] == "full":
        add(embed(".gitignore"))
    else:
        add("#### G:\\CodeWeave\\.gitignore（关键行节选，带原行号 / 共 %d 行）\n\n````text\n%s\n````\n" % (len(lines_of(".gitignore")), gitignore_excerpt(L["gimax"])))
    add("另有 `网页端/项目/vitest.config.ts`、`网页端/项目/eslint.config.js`（测试/Lint 配置，低优先级，未内联，存在性见 §2 目录树）。\n")

    # ===== 6 技术栈 =====
    add("## 6. 技术栈判断（每端，附证据行）\n")
    add("| 端 | 框架/语言 | 构建/工具链 | 证据（文件:行） |")
    add("|---|---|---|---|")
    add("| 网页端 | React 19.2.8 + TypeScript 5.9.3（TSX）；后端为零依赖纯 Node HTTP 服务（node:http） | Vite 8.2.1（Rolldown 内核，见 vite.config.ts:23 注释）+ tsc -b；Vitest ^4.1.11；ESLint ^10.8.1；Node ^22.13.0\\|\\|>=24（.nvmrc=24） | %s；%s；%s；%s；G:\\CodeWeave\\网页端\\项目\\server\\service\\server.mjs:1；%s |" % (EV["react"], EV["vite"], EV["ts"], EV["vitest"], EV["entry"]))
    add("| 应用端 | C++23 业务核心 + Win32 原生壳（main.cpp，1378 行）；可选 Qt 6.8.3 Quick/QML 壳（CodeWeaveQtShell，CMake 选项 QEWEAVE_BUILD_UI_QT） | CMake ≥3.25 + MSVC（静态运行时）；Node ≥24 仅用于构建期工具（内容导出/打包/测试），产品运行不依赖 Node/网页服务 | %s；G:\\CodeWeave\\应用端\\项目\\native\\ui-qt\\CMakeLists.txt:3（find_package(Qt6 6.8.3 REQUIRED COMPONENTS Quick Qml QuickControls2)）；%s；G:\\CodeWeave\\应用端\\项目\\native\\CMakeLists.txt:4 |" % (EV["cxx23"], EV["appdesc"]))
    add("| 移动端 | Kotlin 2.0.21 + Jetpack Compose（Material3 1.3.2，仅骨架页）；C++20 共享核心 mobile-core（SHARED 库） | Gradle 8.9 Wrapper + AGP 8.7.3（SHA-256 固定）；compileSdk 35 / minSdk 26 / JDK 17 toolchain；mobile-core 用 CMake ≥3.22 独立构建 | %s；%s；%s；%s；G:\\CodeWeave\\移动端\\项目\\mobile-core\\CMakeLists.txt:3–5 |" % (EV["agp"], EV["kotlin"], EV["compilesdk"], EV["material3"]))
    add("")
    add("补充：网页端开发态 `vite dev`（端口 5173）把 `/api` 代理到 resolveApiOrigin 解析的本机服务（vite.config.ts:47–67，changeOrigin:false 保持 Host 透传以通过服务端同源校验）；生产/预览为同源相对路径，preview（4173）显式无代理（vite.config.ts:70–79）。网页服务默认 127.0.0.1:4173（server/config/codeweave.config.example.json）。应用端 Qt 壳在构建期还会把 网页端/项目/src/engine/teaching-runtime.ts 导出为 teaching-runtime.js 打进 Qt 资源（ui-qt/CMakeLists.txt:10–16,41–42）——跨端构建期依赖，运行期不依赖。\n")

    # ===== 7 内容消费现状 =====
    add("## 7. 内容消费现状（重点）\n")
    add("### 7.0 结论摘要\n")
    add("1. **CodeWeave 不是内容消费空白**：网页端已有完整的「Obsidian 资料库（vault）→ 受限 frontmatter 解析 → 编译为版本化内容快照 → 同源 API → 前端受限 Markdown 渲染」管线，另有「学习证据 → 预览/确认 → 写回资料库（可回滚）」的双向通道。")
    add("2. **manifest 数据契约已经存在**：网页服务读取库根相对路径 `CodeWeave/content-manifest.json`（content/index.mjs:14），强校验 schemaVersion===1 与稳定 vaultId。Gemini 建议的「资料库输出 manifest.json」与现有实现同向——落地点是让 fullstack-study-library 产出**与现有契约兼容**的清单，而非新发明一套；字段契约见 §7.2。")
    add("3. **应用端（Qt/Win32）课程内容不走 manifest**：构建期从网页端内置课程（src/data/*.ts）导出只读内容包 native/content；运行期对资料库只做拥有者绑定、进度只读投影与证据写回（应用端 grep `content-manifest` 仅命中发布预检清单 scripts/native-preflight.mjs:6）。")
    add("4. **移动端未发现任何内容加载逻辑**（grep manifest/vault/obsidian/markdown/资料库/frontmatter 仅命中 AndroidManifest.xml 的 XML 标签名）。\n")
    add("### 7.1 网页端：资料库根解析与 manifest 读取\n")
    add("- 库根解析：server/service/server/config.mjs — KNOWN_KEYS={schemaVersion,vaultRoot,dataDir,port,staticDir}（:64）；优先级 CLI > env CODEWEAVE_VAULT_ROOT/CODE_CANVAS_DATA_DIR/PORT > config/codeweave.local.json > 默认 vaultRoot=`<工程根>/data/knowledge/vault`、dataDir=`data/runtime/data`、port=4173（:151–156）；监听固定 127.0.0.1。")
    add("- 清单与同步日志常量（index.mjs:14–16）：`MANIFEST_PATH='CodeWeave/content-manifest.json'`；`SYNC_LOG_PATH='CodeWeave/同步报告/同步记录.json'`（上限 30 条）。")
    add("- loadManifest 校验 + writeManifest 原子写回（只更新 topics/publishedContentIds，其余字段原样保留）：\n")
    add(embed("网页端\\项目\\server\\service\\server\\content\\index.mjs", 28, L["indexend"], numbered=True))
    add("- 发布是带日志阶段的事务（publishTransaction，index.mjs:106–130，阶段含 'manifest'，可恢复）；快照由 snapshot.mjs createSnapshotStore 管理（保留份数常量 KEEP_SNAPSHOTS 值未读取，未确认）；门面只暴露校验后快照，不暴露绝对路径、不接受客户端传磁盘路径（index.mjs:1–6 注释）。\n")
    add("### 7.2 网页端：内容编译器与 manifest 字段契约\n")
    add("compileContent 入口（G:\\CodeWeave\\网页端\\项目\\server\\service\\server\\content\\compiler.mjs:825–864，文件头 :2 自述「内容编译器（LINK-04）：资料库 → 候选内容包」，单向只读）：\n")
    add(embed("网页端\\项目\\server\\service\\server\\content\\compiler.mjs", 825, 825 + L["compiler"] - 1, numbered=True))
    add("**代码实际消费的 manifest 字段**（据 index.mjs / compiler.mjs，仓库内未发现独立 JSON Schema 文件，完整字段表以代码为准）：\n")
    add("| 字段 | 约束/用途 | 证据 |")
    add("|---|---|---|")
    add("| schemaVersion | 必须 ===1，否则 invalid_manifest | content/index.mjs:48–50 |")
    add("| vaultId | 非空字符串（稳定库 ID），进入快照 bundle.vaultId | content/index.mjs:51–53；compiler.mjs:993 |")
    add("| publishWhitelist | 发布白名单（必需）；代码引用其 topicIndexPath（与资料库侧 build_topic_index.py 产物逐册比对，缺失→warning topic_index_absent）、topicIdMapPath（主题 ID 映射，schemaVersion 高于支持版本→unsupported_id_map） | compiler.mjs:49–52,845–854,1033–1042 |")
    add("| sourceRegistry | 来源卡登记，含 verificationStatus；未登记来源拒绝 | compiler.mjs:291,896；contracts/validation-codes.yaml:221,249 |")
    add("| topics | 主题 ID 登记表（源资产，非缓存）：同步时刷新（added/moved/retired），历史有主题而被清空→拒绝重建；同步后写回 manifest | compiler.mjs:855–863,915,1073–1102；validation-codes.yaml:268 |")
    add("| publishedContentIds | 同步后由 writeManifest 更新 | content/index.mjs:57 注释 |")
    add("")
    add("其他编译约束：单主题上限 maxTopicBytes=200_000（compiler.mjs:825）；扫描/教学单元/练习均经受限 frontmatter 解析（scanVolumes:267、loadTeachingUnits:371、loadExercises:466）。\n")
    add("### 7.3 网页端：受限 frontmatter 子集（与资料库 Python 工具同语义）\n")
    add("markdown.mjs 文件头（:2–11）自述：只解析受限 frontmatter 子集=顶层 key:value 标量+行内 [a,b] 列表，子集外报 frontmatter_unsupported，不猜测不降级；与资料库侧 `tools/check_vault.py`、`tools/build_topic_index.py` 同语义。解析器：\n")
    add(embed("网页端\\项目\\server\\service\\server\\content\\markdown.mjs", 99, L["mdend"], numbered=True))
    add("路径安全：vault-paths.mjs 提供 resolveInsideRoot/resolveVaultRoot/readVaultText/listMarkdownFiles；`..`、绝对路径、盘符、symlink/junction 逃逸一律 path_escape（README-attachments.md:40–44 引 vault-paths.mjs:85）；拒绝 . 开头目录段（.obsidian 等不入库扫描）。\n")
    add("### 7.4 网页端：HTTP 层与前端渲染\n")
    add("- server.mjs:26–31：content/learning 服务只把派生数据落应用数据目录，「不从资料库根直接对外提供」；同步限流 CONTENT_SYNC_MAX=30。错误映射 vault_unavailable→503、invalid_manifest/source_changed/publish_failed→409（:438–454）；/api/content/* 一律要求已登录（:460–474），默认私人。")
    add("- 前端：src/content/types.ts:9 `ContentSourceKind='vault'|'legacy-fallback'|'none'`；provider.tsx 已登录才拉快照，未登录/未连接走**显式** legacy 回退（内置课程），暴露 bindVaultOwner/unbindVaultOwner/loadVaultProgress/证据暂存；adapter.ts（LINK-05）把快照映射为 Lesson/CurriculumStage，hasVaultContent 以 contentId 判定；api.ts 只调同源 /api（fetchVaultProgress→'/api/learning/vault-progress':227）。")
    add("- 渲染：markdown.tsx 受限 Markdown（无 dangerouslySetInnerHTML/innerHTML、不生成 href，唯一 src 出口=同源 /api/content/asset?path=…，见 §4 README-attachments.md:17–18）；wikilink.ts 按 Obsidian 口径解析双链/别名（:82 别名取第一个未转义 | 之后，:235 未连接快照→unresolved）；复习间隔权威文本在资料库 `knowledge/vault/CodeWeave/rules/teaching-rules.json`，由 compiler.mjs:1178 编译进快照（src/data/mastery.ts:54–56；兜底 0,1,3,7,14,30 天）。")
    add("- 设置入口：app.tsx:1011–1013 `<details className=\"desktop-vault-settings\"><summary>资料库连接与拥有者设置</summary><VaultBindingPanel/>`。\n")
    add("### 7.5 硬编码的资料库布局契约（比 manifest 更强的落地约束）\n")
    add("两端代码写死了以下库根相对路径，资料库目录/文件名变更必须同步改两端代码：\n")
    add("| 路径（库根相对） | 用途 | 证据 |")
    add("|---|---|---|")
    add("| CodeWeave/content-manifest.json | 内容清单（读+受控写回） | content/index.mjs:14；learning/index.mjs:42–43 |")
    add("| CodeWeave/同步报告/同步记录.json | 同步日志（上限 30 条） | content/index.mjs:15–16 |")
    add("| 全栈工程师学习计划/进度追踪.md | 正式进度只读投影 + 写回目标 | learning/progress.mjs:17；ui-qt/facade/vault_writeback_store.cpp:37 |")
    add("| 全栈工程师学习计划/全栈竞赛长期冲刺总计划.md | 总计划日志索引写回目标 | learning/writeback.mjs:27；vault_writeback_store.cpp:38 |")
    add("| knowledge/vault/CodeWeave/rules/teaching-rules.json | 复习间隔规则权威文本 | src/data/mastery.ts:54–56 |")
    add("| tools/check_vault.py、tools/build_topic_index.py | 资料库侧校验/主题索引工具（被引用为同语义基准与索引生成器） | content/markdown.mjs:2–11；compiler.mjs:1033–1042 |")
    add("")
    add("Qt 绑定拥有者时要求 进度追踪.md 与 总计划.md 两文件必须已存在（vault_writeback_store.cpp:313–316）。\n")
    add("### 7.6 学习数据写回（双向通道，两端各自实现）\n")
    add("- 网页端：learning/owner.mjs 在应用数据目录维护 vault-owner.json {schemaVersion,vaultId,ownerUserId,boundAt,publicContent}（owner_taken/not_owner）；evidence.mjs 证据先 pending 落应用数据、不触库；writeback.mjs（:258 createWritebackService）是「本项目第一次写资料库文件」：预览→确认→提交（带备份:783）→可回滚（:873），顺序 学习日志→进度追踪→总计划日志索引（测试断言）；错误码 owner_unbound/forbidden/vault_unavailable。")
    add("- 应用端 Qt：facade/vault_writeback_store.cpp — 单文件上限 8MB（:35）、锁 learning/vault-writeback.lock（:243）、拥有者记录 learning/vault-owner.v1.json（:290）、canonicalFilePath 防别名（:304）；facade/ui_shell.hpp:137–144 暴露 Q_INVOKABLE bindVaultOwner/previewVaultWriteback/commitVaultWriteback(operationId,expectedHashes)/rollbackVaultWriteback；platform/ui_main.cpp:259–279 用 QSettings 'vault/root' 存库根，对话框文案「选择资料库根目录（仅连接，确认提交前不修改资料库）」。")
    add("- 原生核心的只读绑定校验（G:\\CodeWeave\\应用端\\项目\\native\\src\\content_access.cpp:82–93）：\n")
    add(embed("应用端\\项目\\native\\src\\content_access.cpp", 82, 93, numbered=True))
    add("- 数据所有权契约（G:\\CodeWeave\\应用端\\工程文件\\A2数据兼容契约.md，73 行）：\n")
    if L["a2table"]:
        add(embed("应用端\\工程文件\\A2数据兼容契约.md", 16, 27, numbered=True))
        add("要点：部分正式学习事实**以 vault 文件为权威**（:23）；内容/附件快照不打入安装包，用户选择路径只读扫描+hash/版本校验（:24）；原生数据根默认 %LOCALAPPDATA%/CodeWeave，可用 CODEWEAVE_NATIVE_DATA_ROOT 覆盖（:38）；旧资料库保持只读边界、不暗中回写（:73）。\n")
    else:
        add("数据分类表（:16–27）把数据分为：正式学习事实（部分**以 vault 文件为权威**，:23）、派生快照（内容/附件快照不打入安装包，用户选择路径只读扫描+hash/版本校验，:24）、应用私有数据（账户/会话/设置）。原生数据根默认 %LOCALAPPDATA%/CodeWeave，可用 CODEWEAVE_NATIVE_DATA_ROOT 覆盖（:38）；旧资料库保持只读边界、不暗中回写（:73）。\n")
    add("### 7.7 应用端：课程内容=构建期导出的只读内容包（不走 manifest）\n")
    add("导出器 G:\\CodeWeave\\应用端\\项目\\scripts\\export-native-content.mjs（129 行）：构建期读 `../../网页端/项目/src/data/{curriculum,lessons,challenges}.ts`（:14–25，stripTypeScriptTypes + data:URL import，记录源 sha256），生成 native/content；ID 规则 /^[A-Za-z0-9_-]{1,120}$/ 且去重（:63）；TSV 值 hex 编码（:9）；拒绝符号链接与未知输出文件（:101–123）。核心段：\n")
    add(embed("应用端\\项目\\scripts\\export-native-content.mjs", 58, 58 + L["export"] - 1, numbered=True))
    add("产物（G:\\CodeWeave\\应用端\\项目\\native\\content\\，93 个文件）：catalog.v1.tsv（%d 课）+ exercises/starter-code/metadata/hints 四个 .v1.tsv + 每课正文 txt 与 hints/ + curriculum.v1.json（6951 行，{schemaVersion:1,sourceHashes,stages,lessons(剥离progress),challenges}）。catalog 首行 hex 解码示例：%s。" % (len(catalog_lines), cat_decoded))
    add("catalog.v1.tsv 首行原文（hex 编码）：\n")
    add(embed("应用端\\项目\\native\\content\\catalog.v1.tsv", 1, L["catn"]))
    add("运行期校验：content_repository.cpp 拒绝符号链接/非法 UTF-8/哈希不匹配/重复 ID/未知文件（native/README.md）；.gitattributes 对 **/native/content/** 设 -text 保字节保真（SHA-256 载荷）。**Qt 运行期不读 content-manifest.json**（应用端 grep 仅命中 scripts/native-preflight.mjs:6 发布产物清单）；Qt 课程=打包内置课程，资料库连接仅用于绑定/进度/写回（§7.6）。\n")
    add("### 7.8 附件白名单与渲染安全边界\n")
    add("G:\\CodeWeave\\网页端\\项目\\server\\contracts\\asset-whitelist.json（98 行，schemaVersion:1）：image=png/jpg/jpeg/gif/webp（可内嵌），document=pdf（服务端可读、客户端不内嵌），text=txt/csv/json（强制 text/plain）；neverOpened 排除 svg/html/htm/xhtml/xml/js/mjs/cjs/css/md/exe/sh/ps1；路径规则为顺序清单（控制/零宽字符→空→长度 300→HTML 片段→绝对/UNC→协议形→%2e→..→非法段字符），前后端与契约三方对齐（wikilink.ts/asset.mjs/本契约，加载时逐项比对漂移即抛错）。接口 GET /api/content/asset?path=<库根相对路径>，判定链与错误口径见 §4 README-attachments.md。\n")
    add("### 7.9 现状、缺口与未确认项（供方案决策）\n")
    add("- **本机未配置真实资料库根**：server/config/ 只有 example（无 codeweave.local.json）；server/data/ 不存在（glob 无文件）；.env.local 只有开发代理 origin，无 CODEWEAVE_VAULT_ROOT；Qt 库根存于 QSettings（注册表/ini）不在仓库内。**两端实际库路径均未确认**；fullstack-study-library 是否已产出 CodeWeave/content-manifest.json 不在本仓范围，未确认。")
    add("- 工程文档自述边界：正式账户/资料库联调未执行（修缮终验报告-20261111.md:11,45,73）；网页门禁 87 测试文件/1296 项通过、覆盖率 89.77%/83%/87.44%/92.79%，Qt Release/CTest 11/11（修缮逐项核对-20261108.md:8,94–98）；Android APK 未编译（本机无 Android SDK，移动端/项目/README.md）。")
    add("- API 契约：contractVersion 1.0.0 / OpenAPI 3.1.0，28 operations/62 errorCodes/4 schemas，三 yaml 源 sha256 固化（server/contracts/generated/sync-manifest.json，generatedAt 2026-10-02）；前端只读消费 generated/api-types.ts，contract:sync 校验四文件存在（scripts/sync-contract.mjs）。")
    add("- 回退语义：资料库未连接时网页端**显式**回退内置课程（legacy-fallback），应用端始终用打包内容——断连不会无内容可用，但 manifest 契约目前只在网页端生效。manifest 无独立 JSON Schema 文件（未发现），字段契约散在 compiler.mjs/index.mjs/validation-codes.yaml；资料库侧生成 manifest 建议以 §7.2 字段表 + §7.5 路径表为兼容目标。移动端未发现内容加载逻辑（§7.0 第 4 条）。\n")

    # ===== 8 主入口 =====
    add("## 8. 主入口文件（节选）\n")
    add("### 8.1 网页端\n")
    add(embed("网页端\\项目\\index.html"))
    add(embed("网页端\\项目\\src\\main.tsx"))
    add(embed("网页端\\项目\\src\\app.tsx", 1, L["apptsx"], note="根组件 app.tsx 共 1382 行，此处为 import 段"))
    add("### 8.2 网页服务\n")
    add(embed("网页端\\项目\\server\\service\\server.mjs", 1, L["servermjs"], note="共 1223 行；内容/学习服务装配见 :26–31"))
    add("### 8.3 应用端\n")
    add(embed("应用端\\项目\\native\\src\\main.cpp", 1, L["maincpp"], note="Win32 壳入口共 1378 行；Qt 壳入口为 native/ui-qt/platform/ui_main.cpp（未内联，见 ui-qt/CMakeLists.txt:27）"))
    add("### 8.4 移动端\n")
    if L["mainactivity"]:
        add(embed("移动端\\项目\\mobile-app\\src\\main\\java\\com\\codeweave\\mobile\\MainActivity.kt", 1, L["mainactivity"]))
    else:
        add(embed("移动端\\项目\\mobile-app\\src\\main\\java\\com\\codeweave\\mobile\\MainActivity.kt"))
    add(embed("移动端\\项目\\mobile-app\\src\\main\\AndroidManifest.xml"))

    add("---\n")
    add("附注：本报告由只读扫描自动生成（_cw_build_report.py），嵌入内容均为磁盘原文；行号以扫描时文件状态为准。验收证据 README 全文与 .local/.claude/工作区 内容未收录（预算/隐私纪律）；Qt SDK（开发环境/）内未发现 README。")
    return "\n".join(S)

LEVELS = [
    dict(attach=45, design=20, apptsx=45, servermjs=30, maincpp=40, uiqt=50, gitignore="full", codestruct=True, evidence="list", compiler=40, export=40,
         webreadme=None, nativecmake=None, vite="full", tsconfignode=True, gradleprops=True, a2table=True, indexend=64, mdend=125, catn=2, gimax=22,
         certreadme=None, settingsgradle=True, mainactivity=None),
    dict(attach=30, design=12, apptsx=30, servermjs=22, maincpp=30, uiqt=40, gitignore="excerpt", codestruct=False, evidence="list", compiler=32, export=32,
         webreadme=None, nativecmake=None, vite="full", tsconfignode=True, gradleprops=True, a2table=True, indexend=64, mdend=125, catn=2, gimax=22,
         certreadme=None, settingsgradle=True, mainactivity=None),
    dict(attach=25, design=10, apptsx=25, servermjs=18, maincpp=25, uiqt=35, gitignore="excerpt", codestruct=False, evidence="count", compiler=28, export=28,
         webreadme=None, nativecmake=None, vite="full", tsconfignode=True, gradleprops=True, a2table=True, indexend=64, mdend=125, catn=2, gimax=22,
         certreadme=None, settingsgradle=True, mainactivity=None),
    dict(attach=12, design=6, apptsx=8, servermjs=10, maincpp=12, uiqt=12, gitignore="excerpt", codestruct=False, evidence="count", compiler=16, export=16,
         webreadme=28, nativecmake=26, vite="excerpt", tsconfignode=False, gradleprops=False, a2table=False, indexend=55, mdend=112, catn=1, gimax=8,
         certreadme=10, settingsgradle=False, mainactivity=25),
]

final, used = None, None
for i, L in enumerate(LEVELS):
    text = build(L)
    n = len(text.encode("utf-8"))
    print("level %d -> %d bytes" % (i, n))
    if n <= BUDGET:
        final, used = text, i
        break
if final is None:
    final, used = text, len(LEVELS) - 1
    print("WARNING: still over budget at last level")

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(final)

print("written:", OUT)
print("bytes:", len(final.encode("utf-8")), "level:", used)
for chunk in final.split("\n## "):
    title = chunk.split("\n", 1)[0][:40]
    print("  section %-42s %d bytes" % (title, len(chunk.encode("utf-8"))))
print("TREE bytes:", len(TREE.encode("utf-8")))
print("total files (excl):", total_files, "top:", top_counts, "privacy:", privacy_counts)
print("readmes: all=%d evidence=%d sdk=%d flagged=%s" % (len(all_readmes), len(evidence_readmes), len(sdk_readmes), flagged))
print("catalog lessons:", len(catalog_lines), "decoded first:", cat_decoded)
print("EV:", EV)
