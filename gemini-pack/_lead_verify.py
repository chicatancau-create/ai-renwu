# -*- coding: utf-8 -*-
"""Lead 验收：定点存在性检查 + 抽样 frontmatter + 报告尺寸。只读，不递归大目录。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
LIB = r'E:\OBsidian\全栈工程师学习资料库'
PACK = r'G:\AIrenwu\gemini-pack'

checks = [
    'CodeWeave', 'CodeWeave/content-manifest.json', 'CodeWeave/同步报告/同步记录.json',
    'tools', 'tools/check_vault.py', 'tools/build_topic_index.py', 'tools/catalog_tool.py',
    'scripts', 'knowledge', 'knowledge/vault', '全栈工程师学习计划',
    '全栈工程师学习计划/进度追踪.md', 'teaching-rules.json', 'manifest.json', 'weave-index.json',
    'build-index.js', '05-外部资料库/材料清单.md',
]
print('--- CodeWeave 硬编码路径在资料库中的存在性 ---')
for c in checks:
    print(('EXISTS ' if os.path.exists(os.path.join(LIB, c)) else 'MISSING'), c)

print('--- 库根一级条目 ---')
for e in sorted(os.listdir(LIB)):
    print(('DIR ' if os.path.isdir(os.path.join(LIB, e)) else 'FILE'), e)

p = os.path.join(LIB, 'scripts')
if os.path.isdir(p):
    print('--- scripts/ 内容 ---')
    print(sorted(os.listdir(p)))

p = os.path.join(LIB, '90-历史归档')
if os.path.isdir(p):
    print('--- 90-历史归档 一级 ---')
    print(sorted(os.listdir(p)))
    for root, dirs, files in os.walk(p):
        if os.path.basename(root) == '全栈工程师学习计划-recover':
            print('--- recover 目录:', root)
            print('dirs:', sorted(dirs)[:30])
            print('files:', sorted(files)[:30])
            break

print('--- 01-阶段课程 自有笔记抽样（前 3 份 md 的开头 8 行）---')
n = 0
for root, dirs, files in os.walk(os.path.join(LIB, '01-阶段课程')):
    dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '__pycache__')]
    for f in sorted(files):
        if f.endswith('.md'):
            fp = os.path.join(root, f)
            with open(fp, 'r', encoding='utf-8', errors='replace') as fh:
                head = fh.read(400)
            print('###', os.path.relpath(fp, LIB))
            print('\n'.join(head.split('\n')[:8]))
            n += 1
            if n >= 3:
                break
    if n >= 3:
        break

print('--- gemini-pack 文件尺寸 ---')
for f in sorted(os.listdir(PACK)):
    fp = os.path.join(PACK, f)
    if os.path.isfile(fp):
        print(f, os.path.getsize(fp))
