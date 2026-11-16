---
title: "pwsh 管道把 UTF-8 中文重编码，致 JSON 解析报假语法错"
date: 2026-11-15
domain: common
category: 工程规范与安全
status: verified
severity: medium
stack: [PowerShell 5.1, Python, JSON]
tags: [编码, 管道, JSON, 假错, Get-Content, UTF-8]
---

# 问题：`Get-Content ... | python` 报 JSON 语法错，但文件本身完全合法

> verified：已最小复现（108 字节文件经管道变 143 字节），并回读原始字节确认是重编码而非解析器 bug。

## 一句话结论

**中文 Windows 上 `Get-Content` 默认按系统代码页（GBK）解码文件**，UTF-8 中文字节被错误解码后再编码写进管道 → 字节数变化、生出控制字符 → 下游 `json.load(sys.stdin)` 报"缺逗号/非法控制字符"。**让子进程自己 `open(path, encoding='utf-8')` 就没事**，不要在管道上想办法转码。

## 触发条件与影响

- 项目或功能：任何"pwsh 读文件 → 管道喂给 python/node 解析"的校验、巡检、一次性脚本
- 环境与版本：Windows + Windows PowerShell 5.1（`5.1.28000.3086`）；文件为 UTF-8（无 BOM）；内容含中文
- 触发条件：命令形如 `Get-Content x.json -Raw | python -X utf8 script.py`，被解析文件里有非 ASCII 字符
- 影响范围：
  - 把**合法配置判成语法错误**，进而误改配置或误报"文件损坏"
  - 长度/字节比对、正则匹配、哈希校验全部失真（中文一变，什么都对不上）
  - 报错行号列号指向中文字符附近时最容易骗人

## 复现步骤

1. 前置条件：临时文件 `%TEMP%\json_pipe_test.json`，108 字节，内容含中文注释：
   ```json
   { "_comment": "中文注释：用来说明留白 8px 的差异", "zone_w": 0.86 }
   ```
2. 直接让 python 打开文件读：
   ```
   python -X utf8 -c "import json;json.load(open(r'<路径>',encoding='utf-8'));print('OPEN_OK')"
   ```
3. 改成管道喂进去：
   ```
   Get-Content <路径> -Raw | python -X utf8 -c "import json,sys;json.load(sys.stdin)"
   ```
4. 预期结果：两种方式都应解析成功。
5. 实际结果：第 2 步 `OPEN_OK`；第 3 步失败。

## 证据

- 管道读到的原始字节（python 打印 `sys.stdin.buffer.read()`）：**143 字节**，而文件是 **108 字节**；中文已变成乱码碎片：
  ```
  b'{ "_comment": "\xe6\xb6\x93\xee\x85\x9f...
  ```
- 管道方式报错：
  ```
  json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 59 (char 58)
  ```
- 同一根因在真实配置文件（约 7KB、42 个键）上的表现：
  ```
  json.decoder.JSONDecodeError: Invalid control character at: line 5 column 231
  ```
  （同一文件用 `open()` 直读则完全正常，键数、值全部正确。）
- 字节数 108 → 143 是关键判据：**经过管道的不是原字节**。

## 根因分析

- 已确认的根因：`Get-Content` 未指定 `-Encoding` 时按系统 ANSI 代码页解码输入字节。UTF-8 的多字节中文在 GBK 视野里是"非法/半合法序列"，被替换成其他字符；PowerShell 写管道时按自身编码重新编码，字节长度与内容都变了，某些替换结果正好落在 C0 控制字符区间 → JSON 严格模式直接拒绝。
- 排除过的假设：
  - 不是 `json` 太严格：同一文件 `open()` 直读通过。
  - 不是 `-X utf8` 没生效：管道模式下解码发生在上游 PowerShell，python 只能收到已被改写的字节。
  - 不是文件本身坏了：文件从未被写入，哈希未变。
- 问题归属：环境/工具链特性（PowerShell 5.1 + 中文代码页），与业务代码无关。

## 最小修复

做法：**取消"管道传内容"这一环，只传路径**。

```powershell
# 不要这样
Get-Content $cfg -Raw | python -X utf8 check.py

# 这样
python -X utf8 check.py $cfg        # 由 python 自己 open(path, encoding='utf-8')
```

若确实必须用管道传内容，用字节通道而不是文本通道：
```powershell
[System.IO.File]::ReadAllBytes($cfg) | ...   # 或用 cmd /c type 且确认下游按字节收
```
注意 `Get-Content -Encoding UTF8` 只是让"解码"正确，**不保证写管道时不重新编码**，仍属高危写法；能传路径就传路径。

影响面：仅改调用方式，不动被解析文件、不动解析器。

## 验证记录

- [x] 格式化或静态检查：不涉及
- [x] 类型检查或编译：不涉及
- [x] 单元、集成或端到端测试：同一文件两种读法对照（`OPEN_OK` vs `JSONDecodeError`），并打印两侧字节数与原始字节
- [x] 构建：不涉及
- [x] 启动或手动回归：修复后在真实配置（42 键）上直读校验通过

## 可复用规则

1. **命令里有中文文件 + 管道 + 解析器，先怀疑编码，不要先改被解析的语法。**
2. 判"管道是否改写了字节"只需一比：`文件字节数` vs `管道收到的字节数`，不等即被改写。
3. JSON/XML/YAML 报错行号落在中文附近、且报的是"缺分隔符/非法控制字符"这类结构性错误时，第一条怀疑对象是编码而非语法。
4. 一次性校验脚本一律"传路径不传内容"；需要内容就用 `open(path, encoding='utf-8')` 或字节 API。
5. 同类现象还有"回显乱码"（只影响显示）——**本条的危害更大：它会让程序做出错误判断**。

## 适用范围与不适用范围

- 适用：Windows PowerShell 5.1（及任何默认按 ANSI 代码页读文本的 shell）向子进程管道传含非 ASCII 的文本；中文/日文/韩文等非 ASCII 内容更易触发。
- 不适用：pwsh 7（默认 UTF-8）下此坑概率大幅降低，但"传路径不传内容"仍是更稳的写法；纯 ASCII 内容不触发；直接 `open(path)` 不受影响。

## 剩余风险

- 若下游程序只接受 stdin（无法改造成读路径），需改用字节通道或让 PowerShell 用 `-Encoding UTF8` + 下游按 `utf-8-sig` 容错读取，仍建议加一步"字节数一致性"自检。
- 本机 PATH 上的 `python` 可能是沙箱运行时而非系统 Python，排查时要用绝对解释器路径，否则会误判为"环境缺库"。

## 关联

- 相关记录：[[踩坑-GetContent默认按代码页解码致UTF8中文回显乱码]]（同一根因的"显示"分支，本条是"喂给程序"分支）、[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]（脚本文件侧的同族问题）、[[踩坑-Bash内联传参吞PowerShell变量与反斜杠]]（同为"传参链路改写造成无关报错"）
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码、命令或文档：`Get-Content -Raw | python`、`json.load(sys.stdin)`
