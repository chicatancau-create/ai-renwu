---
title: "CC Switch「系统环境变量冲突」横幅复发：真因是 headroom manifest 被整批写进注册表，且删完必须重启 CC Switch 才消失"
date: 2026-11-24
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [CC Switch 4.0.40, headroom, Python, Windows 11, HKCU Environment]
tags: [环境变量冲突, CC Switch, headroom, manifest, 横幅, 注册表, 重启生效, 端口探测]
---

# 问题：CC Switch 又弹「检测到系统环境变量冲突」，删过的变量又回来了

> `verified`：复现、定位、修复、验证四步均已完成。

## 一句话结论

横幅里的 `ANTHROPIC_TARGET_API_URL` / `OPENAI_TARGET_API_URL` 不是 CC Switch 写的，而是 **headroom 部署 manifest 的 `base_env` 被整批同步进了 `HKCU\Environment`**；删变量后**必须重启 CC Switch**（它读的是启动时快照）横幅才会消失，且重启会重写客户端配置（哈希变、URL 不变），复核要看 URL 不能看 hash。

## 触发条件与影响

- 项目或功能：CC Switch 主窗口顶部黄色横幅；本机 Agent → headroom → cc-switch 代理链。
- 环境与版本：Windows 11；CC Switch 4.0.40；headroom（`D:\uv\tools\headroom-ai`，`python -m headroom.cli proxy --port 8787`）；cc-switch 本地代理 `127.0.0.1:15721`。
- 触发条件：用户级注册表里存在 `ANTHROPIC_*` / `OPENAI_*` / `GEMINI_*` / `GOOGLE_GEMINI_*` / `XAI_*` 前缀变量，CC Switch 启动时一律告警（官方 5.4-env-conflict）。
- 影响范围：横幅只是提示，不阻断代理；真正的隐患是把 headroom 专属变量污染全机环境（如 `HEADROOM_OFFLINE=1` 对所有新进程可见）。

## 复现步骤

1. 前置条件：headroom manifest 已被写入注册表（本机 2026-11-24 现状：27 个 `HEADROOM_*` + 2 个 TARGET_API_URL 与 manifest `base_env` 逐项同名同值，唯一缺 `HF_HOME`）。
2. 操作或命令：启动 CC Switch（静默启动亦可）。
3. 预期结果：主窗口无告警。
4. 实际结果：顶部黄色横幅「检测到系统环境变量冲突 / 发现 2 个环境变量可能会覆盖您的配置」，列出两条 URL，来源标注「用户环境变量（注册表）」。

## 证据

- 横幅文本：`ANTHROPIC_TARGET_API_URL = http://127.0.0.1:15721`、`OPENAI_TARGET_API_URL = http://127.0.0.1:15721/v1`，来源 `HKEY_CURRENT_USER\Environment`。
- CC Switch 自备份：`D:\DevCache\.cc-switch\backups\env-backup-20261124_012335.json`（当时只报 1 条 `OPENAI_TARGET_API_URL`，说明是分批漏进来的）。
- 删完变量、未重启 CC Switch 时截图，横幅**仍在**（读启动快照）。
- 重启后无新增 `env-backup-*.json`，横幅消失。

## 根因分析

- 已确认的根因：headroom 的 `C:\Users\Admin\.headroom\deploy\default\manifest.json` → `base_env`（L22 起）被整批写进 `HKCU\Environment`。两条 TARGET_API_URL 只是这批里的成员，不是独立来源，所以「删了就永不复发」的判断是错的；看是否复发要查注册表里那 27 个 `HEADROOM_*`。
- 消费方事实更正：全局变量**没有**消费方；headroom 启动链自己注入同名变量，三处齐备且都在 `C:\Users\Admin\.headroom\deploy\default\`：`run-headroom.ps1`(L7-L9)、`ensure-headroom.ps1`(L7-L9)、`manifest.json` 的 `base_env`。所以删注册表变量不影响 headroom 上游。
- 排除过的假设：CC Switch 自己写注册表（不会，它只写客户端配置文件）；headroom 代理需要全局变量才能正常路由（不需要，实测删完仍 200）。
- 问题归属：环境或依赖（部署 manifest 被误同步到全局）。

## 最小修复

1. 备份：`$snap | ConvertTo-Json | Set-Content D:\DevCache\.cc-switch\backups\env-manual-backup-<yyyyMMdd_HHmmss>.json`
2. `reg delete "HKCU\Environment" /v ANTHROPIC_TARGET_API_URL /f`，同法删 `OPENAI_TARGET_API_URL`（保留 `CODEX_HOME`）。
3. 广播环境变更：`SendMessageTimeout(HWND_BROADCAST=0xffff, WM_SETTINGCHANGE=0x1A, 0, "Environment", SMTO_ABORTIFHUNG=2, 3000, out r)`。`reg delete` 不发通知，不广播则新进程读不到。
4. 重启 CC Switch：`Stop-Process -Id <pid> -Force` → `Start-Process 'D:\CC Switch\cc-switch.exe'`，约 10 s 后日志出现 `[SRV-001] 代理服务器启动于 127.0.0.1:15721` + `claude attach` / `codex attach`。
5. 验证横幅消失 + 双端口健康 + 端到端各打一发。

## 验证记录

- [x] 格式化或静态检查：不适用（配置类）。
- [x] 类型检查或编译：不适用。
- [x] 单元、集成或端到端测试：`POST http://127.0.0.1:8787/v1/messages`（model=claude-sonnet-5）→ HTTP 200，回 `"OK"`，`model` 被映射成 `deepseek-v4.1-flash`；同一请求打 `15721` → HTTP 200。
- [x] 构建：不适用。
- [x] 启动或手动回归：CC Switch 重启后横幅消失；`15721/health` 与 `8787/health` 均 200；`~/.claude/settings.json` 仍 `ANTHROPIC_BASE_URL=http://127.0.0.1:8787`，`D:\DevCache\.codex\config.toml` 仍 `base_url="http://127.0.0.1:8787/v1"`（headroom 未被静默绕过）。

## 可复用规则

- **判横幅是否复发，看注册表里有没有整批 `HEADROOM_*`**，不要只看那两条 URL。
- **删完用户环境变量必须重启 CC Switch**，横幅读启动快照；重启后若 `backups` 目录新增 `env-backup-*.json`，说明还有冲突源。
- **重启 CC Switch 后核对 URL，不核对 hash**：`~/.claude/settings.json` 与 `config.toml` 必被重写、哈希必变，这是正常 attach 行为。
- **判本地端口死活只用 HTTP 探测（curl `-w "%{http_code}"`）**：`Get-NetTCPConnection -LocalPort 15721 -State Listen` 可能返回空，但 `/health` 返 200。
- 往 CC Switch 的本地端口发 JSON 时，`curl.exe --data-binary` 的文件不能带 BOM（`Set-Content -Encoding utf8` 会带），否则上游报 `malformed JSON` / `expected value at line 1 column 1`；用 `[System.IO.File]::WriteAllText(path, json, [System.Text.UTF8Encoding]::new($false))`。

## 适用范围与不适用范围

- 适用：CC Switch 4.x（任何「本地代理 + 供应商列表」形态的切换器）+ 前置 token 压缩代理（headroom 之类）的串联部署；Windows 用户级注册表环境变量污染。
- 不适用：CC Switch 接第三方网关的四件套配置问题；密钥串栏问题（见关联记录）。

## 剩余风险

- 注册表仍有 27 个 `HEADROOM_*`（含 `HEADROOM_OFFLINE=1`、`HEADROOM_SAVINGS_TARGET=0.50`）。它们不触发横幅（横幅只扫 ANTHROPIC/OPENAI/GEMINI/GOOGLE_GEMINI/XAI 前缀），但违反「只在 headroom 启动链注入」的约定；manifest 已含全量，删除理论安全，本次为降风险未动。
- 根因未封堵：`D:\Skills` 下无脚本写 `HKCU\Environment`（grep 无命中），说明本次是人工/会话一次性同步，暂无自动复发源；但没有「禁止把 manifest 写注册表」的守门脚本，同类操作仍可能再来一次。
- 强杀 CC Switch 不走 detach 路径；本次因客户端本就指向 8787（headroom 存活），15721 只断几秒，无感。若客户端指向 15721，强杀会造成该时段请求失败。

## 关联

- 相关记录：[[踩坑-CCSwitch判claude无法运行且反重力不识别-陈旧npm前缀遮蔽与进程PATH]]（该记录第 42 行「无消费方」结论已被本记录更正）、[[规则-headroom省token串在ccswitch前面并加接线守护]]、[[规则-CCSwitch接OpenAI兼容网关要四件套配置]]、[[踩坑-CCSwitch多供应商共用同一把密钥致换key无效]]
- 相关分类：[[03-通用/03-调试与验证/README]]
- 相关代码、命令或文档：`C:\Users\Admin\.headroom\deploy\default\manifest.json`、`run-headroom.ps1`、`ensure-headroom.ps1`；`D:\Skills\headroom\SKILL.md` L110-140；`D:\Skills\skill-router\SKILL.md` 链路段；全局记忆 `D:\Skills\global-memory\reference-ccswitch-env-conflict-recur-2026-11-24.md`；CC Switch 官方 [5.4-env-conflict](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/zh/5-faq/5.4-env-conflict.md)。
