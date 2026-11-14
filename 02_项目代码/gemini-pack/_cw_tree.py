# -*- coding: utf-8 -*-
# 只读扫描 G:\CodeWeave：目录树(深度4) + 关键文件清单(路径|字节|行数)
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"G:\CodeWeave"
EXCLUDE = {"node_modules", ".git", "dist", "build", "out", ".next", "coverage", "__pycache__", ".venv", ".gradle"}
PRIVACY = {".local", ".claude", "工作区"}
MAXDEPTH = 4

def walk_dirs(d):
    for base, dirs, files in os.walk(d):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUDE and x not in PRIVACY)
        yield base, dirs, files

def count_files(d):
    return sum(len(f) for _, _, f in walk_dirs(d))

def line_count(p):
    try:
        with open(p, "rb") as fh:
            data = fh.read()
        if not data:
            return 0
        return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)
    except OSError:
        return -1

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

BUILD_RE = re.compile(r"^(vite|webpack|rollup|esbuild|next|nuxt|astro|svelte|vue|babel|postcss|tailwind|capacitor|ionic|metro|expo|electron|forge|craco|rspack|farm|vitest|jest|playwright|cypress)\.(config|conf)\.")
BUILD_NAMES = {"tauri.conf.json", "electron-builder.yml", "electron-builder.json", "electron-builder.json5",
               "project.config.json", "app.config.ts", "app.config.js", "angular.json", "vue.config.js",
               "CMakePresets.json"}
NATIVE_NAMES = {"Cargo.toml", "pubspec.yaml", "Podfile", "build.gradle", "build.gradle.kts", "settings.gradle",
                "settings.gradle.kts", "gradle.properties", "manifest.json", "app.json", "pages.json",
                "AndroidManifest.xml", "Info.plist", "project.pbxproj", "Package.swift", "CMakeLists.txt",
                "requirements.txt", "pyproject.toml", "go.mod", "pom.xml", "Gemfile", "composer.json"}
ENTRY_RE = re.compile(r"^(main|index|App|app|entry|bootstrap)\.(ts|tsx|js|jsx|mjs|cjs|vue|svelte|html|py|rs|kt|swift|dart|cpp|cc|cxx)$")
WS_NAMES = {"pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json"}

CATS = [
    ("package.json", lambda n: n == "package.json"),
    ("workspace-monorepo", lambda n: n in WS_NAMES or n.endswith(".code-workspace")),
    ("build-config", lambda n: bool(BUILD_RE.match(n)) or n in BUILD_NAMES),
    ("tsconfig", lambda n: n.startswith("tsconfig") and n.endswith(".json")),
    ("env", lambda n: n.startswith(".env")),
    ("readme", lambda n: n.lower().startswith("readme")),
    ("native-manifest", lambda n: n in NATIVE_NAMES or n.endswith(".csproj") or n.endswith(".pro")),
    ("entry-candidates", lambda n: bool(ENTRY_RE.match(n))),
]

inv = {name: [] for name, _ in CATS}
total_files = 0
for base, dirs, files in walk_dirs(ROOT):
    total_files += len(files)
    for f in files:
        for name, pred in CATS:
            if pred(f):
                p = os.path.join(base, f)
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    sz = -1
                inv[name].append((os.path.relpath(p, ROOT), sz, line_count(p)))
                break

print("=== TOTAL ===")
print("total files (excl EXCLUDE/PRIVACY):", total_files)
print()
print("=== TREE (depth %d) ===" % MAXDEPTH)
print("\n".join(tree_lines))
print()
for name, _ in CATS:
    items = inv[name]
    print("=== %s (%d) ===" % (name, len(items)))
    for rel, sz, lc in sorted(items):
        print("%s | %dB | %d lines" % (rel, sz, lc))
    print()
