#!/usr/bin/env python -X utf8
"""知识库 wikilink 完整性与孤儿检查（Obsidian vault）。

用法：
    python -X utf8 脚本-知识库wikilink完整性与孤儿检查-Obsidian.py [vault根目录]
默认 vault 根 = 本脚本所在目录往上两级再拼「本地AI使用手册」的推导，也可显式传参。

判三件事：
1. DEAD   —— wikilink 指向的目标不存在（Obsidian 裸链接按「文件名」全库解析，这里同规则）
2. ORPHAN —— 记录文件没有任何自身以外的引用（写了但没人能找到）
3. HASH   —— 文件名里含 `#`，这类名字在 Obsidian 里无法被 wikilink 可靠引用
             （官方文档把 # | ^ : %% [[ ]] 列为「不可靠用于链接的字符」，且不提供转义）

2026-11-15 首次全库跑出的两类真实成因（各 2 例，均已修）：
- DEAD 多为「记录改名后入链没跟着改」的漂移。修法是先按关键词全库搜真实文件名再重连，
  不要一删了之——引用句本身常带着有用信息（如「同一部署任务里发现的取数坑」）。
- ORPHAN 多为「写了但没在分类 README 登记」。只补链接即可，别顺手给别人的记录补 frontmatter：
  `status: verified` 是断言，没复现过就不能替别人写。

退出码：0 全部通过；1 有任一项命中。
"""
import io
import os
import re
import sys

LINK = re.compile(r'\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]')


def find_vault_root(argv):
    if len(argv) > 1:
        return os.path.abspath(argv[1])
    here = os.path.dirname(os.path.abspath(__file__))
    for up in (2, 3, 4):
        cand = os.path.normpath(os.path.join(here, *(['..'] * up)))
        hits = [d for d in os.listdir(cand) if os.path.isdir(os.path.join(cand, d)) and 'AI使用手册' in d]
        if hits:
            return os.path.join(cand, hits[0])
    raise SystemExit('找不到 vault 根，请显式传第二个参数')


def main():
    root = find_vault_root(sys.argv)
    md, allfiles = {}, set()
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.git', '.obsidian', 'node_modules')]
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace('\\', '/')
            allfiles.add(rel)
            if f.endswith('.md'):
                md[rel] = io.open(os.path.join(dirpath, f), encoding='utf-8', errors='replace').read()

    # 链接目标可以是脚本/图片等非 .md 附件，只索引 .md 会把它们全判成死链
    stems = {os.path.basename(r) for r in allfiles} | {r for r in allfiles}
    by_name = {}
    for rel in md:
        base = os.path.basename(rel)[:-3]
        by_name.setdefault(base, []).append(rel)
        by_name.setdefault(rel[:-3], []).append(rel)

    def resolves(target):
        for t in (target, os.path.basename(target)):
            if t in by_name or (t + '.md') in by_name:
                return True
            if t in stems or (t + '.md') in stems:
                return True
            if os.path.exists(os.path.join(root, t)) or os.path.exists(os.path.join(root, t + '.md')):
                return True
        return False

    # Obsidian 官方把 # | ^ : %% [[ ]] 列为不可靠字符；单个 % 是合法的（如「显存0%」）
    HASHY = ('#', '%%', '|', '^', '[', ']')
    dead, hashnames = [], []
    for rel, txt in md.items():
        for raw in LINK.findall(txt):
            tgt = raw.split('#', 1)[0] if '#' in raw else raw
            if not (resolves(tgt) or ('#' in raw and resolves(raw))):
                dead.append((rel, raw))
        base = os.path.basename(rel)
        if any(c in base for c in HASHY):
            hashnames.append(rel)

    # 入链既算 wikilink 也算 markdown 式 [x](y)，否则会把有 markdown 引用的记录误判成孤儿
    MDLINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
    linked = set()
    for rel, txt in md.items():
        refs = list(LINK.findall(txt)) + [m.split('#')[0] for m in MDLINK.findall(txt)]
        for raw in refs:
            for t in (raw, raw.split('#', 1)[0], os.path.basename(raw.split('#', 1)[0])):
                t = os.path.splitext(t)[0] if t.endswith(('.py', '.png', '.js')) else t
                for hit in by_name.get(t, ()):
                    linked.add(hit)
                if t in by_name:
                    linked.update(by_name[t])
        # frontmatter 里的 aliases 也算一种被引用方式
        for a in re.findall(r'^\s*-\s*(.+)$', txt.split('---')[1] if txt.startswith('---') else '', re.M):
            for hit in by_name.get(a.strip().strip('"\''), ()):
                linked.add(hit)

    records = [r for r in md
               if os.path.basename(r) != 'README.md'
               and not r.endswith('索引.md')
               and not r.startswith('90-模板')
               # 05-Codex 子库的 README 明确写着「不依赖 Obsidian 才能读取，Obsidian 只是浏览界面」，
               # 它用表格 + 相对路径导航而不是 wikilink，用主库的入链规矩套它必然误报
               and not r.startswith('03-通用/05-Codex工程知识库')
               and os.path.basename(r) not in ('首页.md', 'AGENTS.md', 'AI接入规则.md', '使用与维护说明.md', '收件箱.md')]
    orphans = [r for r in records
               if r not in linked and os.path.basename(r)[:-3] not in linked
               and not any(os.path.basename(r)[:-3] in md[o] for o in ())]

    print(f'vault: {root}')
    print(f'扫描 {len(md)} 个 .md，{len(records)} 条记录\n')
    for label, items in (('DEAD  失效链接', dead), ('HASH  文件名含不可靠链接字符', hashnames), ('ORPHAN 无入链记录', orphans)):
        print(f'--- {label}: {len(items)}')
        for it in items[:25]:
            print('   ', it if isinstance(it, str) else f'{it[0]}  ->  {it[1]}')
        if len(items) > 25:
            print(f'    ...另有 {len(items) - 25} 条')
    bad = len(dead) + len(hashnames) + len(orphans)
    print(f'\n{"全部通过" if not bad else str(bad) + " 处待处理"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
