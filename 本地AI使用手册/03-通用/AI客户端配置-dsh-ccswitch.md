---
title: "AI 客户端配置笔记：dsh / cc-switch / cc-haha 接阿里云百炼与代理绕过"
date: 2026-11-14
domain: common
category: 03-通用
status: verified
severity: low
stack: [DeepSeek Harness, cc-switch, cc-haha, 阿里云百炼, Windows]
tags: [provider配置, ProxyOverride, hosts, 启动慢, 元数据为2026-11-15补登]
---

# AI 客户端配置笔记（dsh / cc-switch / cc-haha）

> 元数据为 2026-11-15 库体检时补登（原记录无 frontmatter），`date` 取正文自述的 2026-11-14。
> `status: verified` 的依据：这是**操作笔记**而非待复现缺陷，内容含具体 exe 路径、注册表键、
> provider id 与实测体积（`01_任务归档` 972MB / `03_备份` 211MB）；其中「系统代理
> `127.0.0.1:7890`」与 2026-11-15 另一次独立实测一致，可作时效旁证。
> 本记录散放在 `03-通用/` 顶层而不在某个细分类目下——**2026-11-15 体检时决定不搬**：
> 移动既有记录属结构改动，且它已登记进 `通用索引.md` 的记录清单、可被检索到，
> 搬动只换来路径洁癖，代价是打断已有的引用与肌肉记忆。要归位的话目标应是 `02-AI协作与提示词/`。

> 记录 2026-11-14 配置阿里云百炼（tokenplan）provider 的完整过程和踩坑。

## 涉及的软件和路径

| 软件 | 路径 |
|------|------|
| DeepSeek Harness (dsh) | `D:\DeepSeek Harness\DeepSeek Harness.exe` |
| cc-switch | `D:\CC Switch\cc-switch.exe` |
| cc-haha (Claude Code Haha) | `D:\Claude Code Haha\Claude Code Haha.exe` |
| cc-switch 数据库 | `C:\Users\Admin\.cc-switch\cc-switch.db` (SQLite) |
| dsh 凭证文件 | `C:\Users\Admin\.dsh\.credentials.yaml` |
| dsh provider 配置 | `C:\Users\Admin\.dsh\profiles\desktop\cordis.patch.yml` |

## 阿里云百炼 provider 配置

### dsh 端配置

**provider id**: `tokenplan`
- **baseURL**: `https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic`
- **api**: `anthropic-messages`
- **apiKeyEnv**: `CC_SWITCH_DSH_TOKENPLAN`
- **models**:
  - `deepseek-v4.1-flash-1017`（reasoning=true，支持 thinking）
  - `qwen4-max-preview`（reasoning=false，不支持 thinking_display=summarized）

### 关键坑：qwen4-max-preview 不支持 thinking_display=summarized

qwen4-max-preview 在阿里云百炼的 Anthropic 兼容端点上，**不认识** `thinking.display=summarized` 参数，会报 400：
```
"thinking_display=summarized is not supported by this model"
```

**解决方法**：在 provider 配置里把 qwen4-max-preview 的 `reasoning` 设为 `false`，`reasoningEfforts` 设为空对象 `{}`。这样 dsh 不会发送 thinking 参数，但模型本身仍会自动返回思考过程。

### 关键坑：cc-switch 会覆盖直接修改

直接改 cc-switch SQLite 数据库后，**必须先杀掉 cc-switch 进程再改数据库**，否则 cc-switch 退出时会把内存中的旧配置写回数据库，覆盖你的修改。正确顺序：
1. `Stop-Process -Name "cc-switch" -Force`
2. 修改 SQLite 数据库
3. 修改 `cordis.patch.yml`
4. 重启 cc-switch

### ECONNRESET 问题

cc-haha 连接阿里云百炼报 ECONNRESET，原因是系统代理 `127.0.0.1:7890` 拦截了 `*.aliyuncs.com`。
- 注册表 `HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings` 的 `ProxyOverride` 追加 `*.aliyuncs.com`
- hosts 文件固定 IPv4：`39.106.104.16 token-plan.cn-beijing.maas.aliyuncs.com`

## dsh 启动慢

dsh 启动时扫描工作区 Git 仓库，`G:\AIrenwu` 下的 `01_任务归档`（972MB）和 `03_备份`（211MB）拖慢加载。把归档目录移出工作区可显著加速。

## 其他默认应用设置

### PotPlayer 设为默认视频播放器

- exe 路径：`D:\_整理\02-便携工具\PotPlayer250123\PotPlayer\PotPlayerMini64.exe`
- 通过注册表 `HKCU:\Software\Classes` 创建 ProgID，关联 43 种视频格式
- 清除 `HKCU:\...\FileExts\.mp4\UserChoice` 等旧关联

### Obsidian 设为 .md 默认打开方式

- exe 路径：`D:\黑曜石笔记\Obsidian\Obsidian.exe`
- 通过注册表 `HKCU:\Software\Classes\Obsidian.md` 创建 ProgID，关联 `.md`
