# -*- coding: utf-8 -*-
"""整合：_header.md + 01 报告 + 02 报告 → 00-上传Gemini-双仓数据包.md。
校验两份报告字节级完整嵌入。只读源报告，只写 00 产物。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
PACK = r'G:\AIrenwu\gemini-pack'

def rd(name):
    with open(os.path.join(PACK, name), 'r', encoding='utf-8') as f:
        return f.read()

header = rd('_header.md')
a = rd('01-CodeWeave-快照.md')
b = rd('02-资料库-快照.md')

sep_a = ('\n\n---\n\n# 第一部分（§A）：CodeWeave 仓库快照（全文嵌入）\n\n'
         '> 扫描员报告原文，未删改。源文件：G:\\AIrenwu\\gemini-pack\\01-CodeWeave-快照.md（69,412 字节 / 1,178 行）\n\n')
sep_b = ('\n\n---\n\n# 第二部分（§B）：全栈工程师学习资料库 仓库快照（全文嵌入）\n\n'
         '> 扫描员报告原文，未删改。源文件：G:\\AIrenwu\\gemini-pack\\02-资料库-快照.md（79,764 字节 / 1,563 行）\n\n')

out = header + sep_a + a + sep_b + b
dst = os.path.join(PACK, '00-上传Gemini-双仓数据包.md')
with open(dst, 'w', encoding='utf-8', newline='\n') as f:
    f.write(out)

with open(dst, 'r', encoding='utf-8') as f:
    back = f.read()
assert header in back and a in back and b in back, 'embedding mismatch'
assert back.count('# 第一部分（§A）') == 1 and back.count('# 第二部分（§B）') == 1
print('OK bytes=', os.path.getsize(dst), 'lines=', back.count('\n') + 1)
print('header_bytes=', len(header.encode('utf-8')),
      'a_bytes=', len(a.encode('utf-8')), 'b_bytes=', len(b.encode('utf-8')))
print('BOM=', open(dst, 'rb').read(3) == b'\xef\xbb\xbf')
