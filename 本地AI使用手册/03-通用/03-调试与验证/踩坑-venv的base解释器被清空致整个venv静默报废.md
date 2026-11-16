---
title: "venv 的 base 解释器目录被清空，致整个 venv 静默报废"
date: 2026-11-13
domain: common
category: 03-调试与验证
status: verified
severity: high
stack: [Python, venv, Windows]
tags: [venv, pyvenv.cfg, 解释器, 静默失败]
---

# 问题：venv 的 base 解释器目录被清空，致整个 venv 静默报废

> 2026-11-15 回写（当时诊断完成、修复未执行）。**2026-11-16 复核升级 verified**：环境已于 11-13 13:07 被另一会话重建，本轮补齐 dev 依赖并全量验证，见文末「复核与修复」节。

## 一句话结论

venv 的 `Scripts/python.exe` 只是 launcher，真正依赖 `pyvenv.cfg` 里 `home` 指向的 base 安装；base 目录被删剩 DLL 后，venv 内所有解释器入口静默报废，而 `site-packages` 看起来完好，极易误判成「包坏了」。

## 触发条件与影响

- 项目或功能：G:\cc-hud 的 `.venv`（CPython 3.14.2 x64，base = `D:\PyCharm\Python`）。
- 环境与版本：Windows 11；`pyvenv.cfg` 的 `home/executable` 均指向 `D:\PyCharm\Python\python.exe`。
- 触发条件：base 目录内容被外部清除（2026-11-13 11:07 目录 mtime；只剩 `DLLs/`、`python3.dll`、`python314.dll`、`pythonw.exe`、两个 vcruntime，共 6 项，无 `python.exe`、无 `Lib/`）。
- 影响范围：pytest、所有 tools/*.py、以及 `start-hud.bat` 拉起的 pythonw 全部不可用；**已在运行的进程不受影响**（DLL 已加载），造成「现在好好的、一重启就死」的假象。

## 复现步骤

1. 前置条件：上述 base 目录残缺状态。
2. 操作或命令：`.venv/Scripts/python.exe -c "print(1)"`。
3. 预期结果：打印 1。
4. 实际结果：`did not find executable at 'D:\PyCharm\Python\python.exe'`，rc=103。
   `.venv/Scripts/pythonw.exe -c "print(1)"` → `Could not find platform independent libraries <prefix>` + `Fatal Python error: Failed to import encodings module`。

## 证据

- `cat .venv/pyvenv.cfg`：`home = D:\PyCharm\Python`、`version = 3.14.2`。
- `ls D:/PyCharm/Python`：6 项，无 python.exe / Lib（2026-11-13 与 11-15 两次实测一致）。
- `.venv/Lib/site-packages` 完好（37 项，含 cp314 的 `.pyd`）→ 包不是问题所在。
- `py -0p` 仍登记 `D:\PyCharm\Python\python.exe`（注册表残留，不代表文件存在）。
- 谁清空的未查明；**不是本会话的操作**（本会话只读该目录）。

## 根因分析

- 已确认的根因：venv launcher 按 `pyvenv.cfg home` 解析 base；base 缺 `python.exe`/`Lib` 即无法初始化。
- 排除过的假设：不是 site-packages 损坏（目录与 .pyd 齐全）；不是 PATH 问题（绝对路径调用同样失败）。
- 问题归属：环境或依赖（外部清除），待确认清除来源。

## 最小修复

**2026-11-16 已完成的实际修复**（与当初候选不同，见复核节）：
1. base 已由另一会话换成完整 CPython 3.15.2（`D:\PyCharm\Python`），venv 由 uv 0.12.15 重建为 cp315，GIL 版（`sys._is_gil_enabled()==True`）。
2. 本轮补 dev 依赖：`uv pip install --python .venv/Scripts/python.exe "pytest>=8"`（装到 pytest 9.2.0），并在 `pyproject.toml` 增加 `[dependency-groups] dev = ["pytest>=8"]`，让重建可复现。
3. 验证：`.venv/Scripts/python.exe -m pytest tests_py` → **114 passed in 1.47s**；`tools/reconcile.py` 四范围 `bad=none`。

当初候选（补 3.14 到 home / 重建 venv）中，**补旧版本一条已被实测否决**：向已有 3.15.2 的 TargetDir 跑 3.14.2 安装器返回 rc=67 拒绝安装——不要往更新的 base 上覆盖旧版本。

## 验证记录

- [x] 复现与定位：两条入口的报错 + base 目录清单 + pyvenv.cfg 三方互证（2026-11-13/11-15）。
- [x] 最小修复：base 重建（另一会话）+ 本轮补 pytest 与 dev 依赖组（2026-11-16）。
- [x] 单元、集成或端到端测试：`pytest tests_py` 114 passed（2026-11-16）。
- [x] 启动或手动回归：`tools/reconcile.py` 1d/7d/30d/all 全 `bad=none`（2026-11-16）。

## 复核与修复（2026-11-16 补充，不覆盖上文历史结论）

- **历史结论有时效**：11-15 写的「base 只剩 6 项、venv 报废」在 11-13 13:07 之后就不成立了——另一会话已把 base 换成 3.15.2 并用 uv 重建 venv（`pyvenv.cfg` 出现 `uv = 0.12.15`、`version_info = 3.15.2`，site-packages 变 cp315）。续接会话先重测再引用旧诊断。
- 本轮真正缺的只是 **dev 依赖**：重建后的 venv 只装了运行时依赖（pywebview/pillow/pythonnet），没有 pytest，也没有 pip；用 `uv pip install --python <venv python>` 补，别假设有 pip。
- 覆盖安装实测：`python-3.14.2-amd64.exe /quiet TargetDir=D:\PyCharm\Python ...` 对已有 3.15.2 的目录返回 **rc=67**（拒绝），未造成破坏；安装包随即删除。
- 清除 base 的来源仍未查明；`D:\PyCharm` 下 IDE 本体也不在，疑似用户卸载/清理所致。

## 可复用规则

- 判 venv 死活第一步跑 `<venv>/Scripts/python.exe -V`；报 `did not find executable at ...` 或 `Failed to import encodings` 时，**先查 pyvenv.cfg 的 home 是否完整**，再怀疑包。
- 「进程还活着」不能证明环境可用：DLL 已加载的旧进程与磁盘上的 launcher 是两回事。
- 重建 venv 前先核对 site-packages 里 `.pyd` 的 cp 版本标签，base 版本必须一致。

## 适用范围与不适用范围

- 适用：Windows 上任何 `python -m venv` 产物（launcher 模型）。
- 不适用：uv/conda 等自带完整解释器的环境（它们不依赖外部 home）。

## 剩余风险

- base 被清空的来源未查明，可能复发；复发时按本记录的判据与修复路径处理。
- venv 现为 3.15.2（GIL 版）；若有人再装 free-threaded 3.15t 并共用 site-packages，会踩 [[踩坑-free-threaded与GIL版共用site-packages致C扩展导入失败-Python]]。

## 关联

- 相关记录：[[踩坑-free-threaded与GIL版共用site-packages致C扩展导入失败-Python]]、[[踩坑-本机执行环境六个静默陷阱-PS反引号wmic缺失pythonw无stdout]]
- 相关分类：03-通用/03-调试与验证（2026-11-16 由收件箱移入）
- 相关代码、命令或文档：G:\cc-hud\.venv\pyvenv.cfg、G:\cc-hud\start-hud.bat