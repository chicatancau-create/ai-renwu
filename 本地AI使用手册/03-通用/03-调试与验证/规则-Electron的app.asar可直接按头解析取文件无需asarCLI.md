---
title: "不装 asar CLI 也能读 Electron app.asar 里的源码：解析 16 字节头 + JSON 目录"
date: 2026-11-01
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: low
stack: [Electron, asar, Python]
tags: [asar, Electron, 逆向, 配置schema, 取证]
---

# 问题：想知道某个 Electron 应用内部插件的配置 schema，但代码全在 app.asar 里

## 一句话结论

`app.asar` 不是压缩包，是「16 字节头 + JSON 目录 + 顺序拼接的文件体」。
用几十行 Python 就能按 offset 精确取出任意内部文件，**不需要 `npm i asar`、不需要 Node**。
拿到插件自带的 `README` / `lib/index.js` 后，配置字段、枚举取值都是本地真源，比翻官方文档快且不会过期。

## 触发条件与影响

- 项目或功能：给第三方 Electron 客户端写配置（本例：DeepSeek Harness 的自定义模型 provider）。
- 环境与版本：Win11 + Python 3.14；目标 `D:\DeepSeek Harness\resources\app.asar`（182 MB）。
- 触发条件：配置 schema 没有公开文档，或文档落后于本地版本。
- 影响范围：不解决就只能猜字段名，写错会**直接导致应用起不来**。

## 复现步骤

1. 前置条件：拿到目标 `app.asar` 路径；确认 Python 可用。
2. 操作或命令：用下面的最小读取器列目录、再提取目标文件。
3. 预期结果：能列出内部文件树，并按路径取出文本文件。
4. 实际结果：18234 个文件全部可枚举，`dsh-llm-pi-ai/README.zh.md` 与 `lib/index.js` 完整取出。

## 证据

```
total files in asar: 18234
matches for 'pi-ai': 276
       1065  dsh/node_modules/@deepseek-ai/dsh-llm-pi-ai/LICENSE
      31708  dsh/node_modules/@deepseek-ai/dsh-llm-pi-ai/README.md
      28721  dsh/node_modules/@deepseek-ai/dsh-llm-pi-ai/README.zh.md
     125589  dsh/node_modules/@deepseek-ai/dsh-llm-pi-ai/lib/index.js
```

从 `README.zh.md` 直接读到字段表与枚举：

```
| apiKeyEnv | 无 | 按请求解析的凭据引用；省略时交由 pi-ai 环境发现 |
| api       | 目录协议 | 协议格式；仅目录不提供的路由需要 |
| baseURL   | 目录端点 | 路由上所有模型的端点 |
```

从 `lib/index.js` 确认 `api` 的三个合法取值：`anthropic-messages` / `openai-completions` / `openai-responses`。

## 根因分析

- 已确认的根因：asar 格式极简——`struct.pack("<4I")` 的第三个字段是 JSON 头长度，
  随后是 pickle 包装的 JSON 目录，每个文件条目带 `offset` / `size`，文件体按 offset 顺序排在头之后。
  基址 = `16 + json_size`。
- 排除过的假设：不是加密、不是压缩（`grep -a` 能直接命中明文，说明未压缩）。
- 问题归属：环境限制（未安装 asar 工具链）。

## 最小修复

```python
import json, struct

ASAR = r"D:\App\resources\app.asar"

with open(ASAR, "rb") as f:
    _, _, _, json_size = struct.unpack("<4I", f.read(16))
    raw = f.read(json_size)
    data = json.loads(raw[raw.find(b"{"):].decode("utf-8", "replace"))
base = 16 + json_size

def walk(node, prefix="", out=None):
    out = [] if out is None else out
    for name, meta in node.get("files", {}).items():
        p = f"{prefix}/{name}" if prefix else name
        (walk(meta, p, out) if "files" in meta
         else out.append((p, meta.get("offset"), meta.get("size"), meta.get("unpacked", False))))
    return out

files = walk(data)
hit = [f for f in files if "关键词" in f[0]]
for p, off, size, unpacked in hit[:40]:
    print(size, p, "[UNPACKED]" if unpacked else "")

# 提取单个文件
target = hit[0][0]
with open(ASAR, "rb") as f:
    f.seek(base + int(hit[0][1]))
    blob = f.read(int(hit[0][2]))
open("out.txt", "wb").write(blob)
```

## 验证记录

- [x] 目录枚举：18234 个文件，路径与大小与磁盘直觉一致。
- [x] 文本提取：取出的 `README.zh.md` 为完整合法 Markdown（28721 字节，与目录记录一致）。
- [x] 交叉验证：从 `lib/index.js` 提取的 `api` 枚举，与 README 表格描述一致；写入配置后 YAML 解析通过。
- [ ] 未做：`unpacked: true` 的条目（文件在 `app.asar.unpacked/` 目录下）未走本读取器验证。

## 可复用规则

**要给某个 Electron 客户端写配置却查不到 schema 时，先去它自己的 `app.asar` 里找插件 README 与源码，
不要先猜字段、也不要只信官网文档。** 判据：`grep -a "关键词" app.asar` 能命中明文 → 直接解析头取文件；
命中为 0 且体积很大 → 该功能不在主包里，去 `resources/runtime`、用户 profile 目录或插件目录找。

## 适用范围与不适用范围

- 适用：未压缩的 Electron asar（绝大多数打包产物）、需要离线取证插件配置的场合。
- 不适用：`unpacked` 条目（需改读 `app.asar.unpacked/`）；加密或二次压缩的自定义打包；
  只读不写——**不要试图回写 asar**，改配置应改应用自己的配置文件层。

## 剩余风险

- asar 目录里的 `offset` 是相对文件体起点的，若用错基址（漏掉 16 字节或漏掉 pickle 前缀）会读到错位内容；
  校验办法：取出的文本文件开头应是可读源码/文档，且字节数与目录记录一致。
- 不同 Electron 版本对 pickle 头的写法可能有细微差异，本记录只用 `raw.find(b"{")` 定位，未做严格解析。

## 关联

- 相关记录：[[踩坑-执行环境Start-Process子进程在工具会话结束时被连带回收]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：`G:\AIrenwu\01_任务归档\2026-11-01_DeepSeek客户端接入WorkBuddy密钥\asar_read.py`（本次使用的完整版读取器，支持列出与提取）
