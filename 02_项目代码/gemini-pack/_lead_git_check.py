# -*- coding: utf-8 -*-
"""只读核查：CodeWeave 期望的路径是否被资料库当前分支跟踪（git ls-files 只读 index，不写）。
输出重定向到真实文件，避免受限沙箱下管道捕获 EPERM。"""
import subprocess, sys, os
sys.stdout.reconfigure(encoding='utf-8')
LIB = r'E:\OBsidian\全栈工程师学习资料库'
OUT = r'G:\AIrenwu\02_项目代码\gemini-pack\_git_paths.txt'
specs = ['CodeWeave/*', 'tools/*', 'knowledge/*', '全栈工程师学习计划/*',
         '*content-manifest*', '*check_vault*', '*teaching-rules*', '*build_topic_index*']
with open(OUT, 'wb') as f:
    for spec in specs:
        f.write(('=== git ls-files -- ' + spec + ' ===\n').encode('utf-8'))
        subprocess.run(['git', '-C', LIB, '-c', 'core.quotepath=false', 'ls-files', '--', spec],
                       stdout=f, stderr=subprocess.STDOUT)
print('done bytes=', os.path.getsize(OUT))
