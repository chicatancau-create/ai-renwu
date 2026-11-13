# -*- coding: utf-8 -*-
"""只读：E:\\OBsidian 一级目录；若存在旧库名 vault，查其 CodeWeave/content-manifest.json。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
OB = r'E:\OBsidian'
print('--- E:\\OBsidian 一级 ---')
for e in sorted(os.listdir(OB)):
    print(('DIR ' if os.path.isdir(os.path.join(OB, e)) else 'FILE'), e)
old = os.path.join(OB, '全栈工程师学习计划')
if os.path.isdir(old):
    print('--- 旧库名 vault 存在，检查关键路径 ---')
    for c in ['CodeWeave/content-manifest.json', 'tools/check_vault.py', '进度追踪.md',
              'knowledge/vault/CodeWeave/rules/teaching-rules.json']:
        print(('EXISTS ' if os.path.exists(os.path.join(old, c)) else 'MISSING'), c)
else:
    print('--- 旧库名 vault 不存在（E:\\OBsidian\\全栈工程师学习计划 MISSING）---')
