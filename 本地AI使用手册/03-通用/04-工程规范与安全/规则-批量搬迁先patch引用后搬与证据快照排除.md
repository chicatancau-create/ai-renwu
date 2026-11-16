# 规则：批量搬迁文件夹——先 patch 引用后搬、证据快照排除

> verified 2026-11-15（G:\AIrenwu 两轮归类实测：第一轮 78 个散文件、第二轮 51 个文件夹 / 156 文件 235 处引用 patch，移动后验证 TOTAL FAILURES: 0）。
> 执行器：`G:\AIrenwu\01_任务归档\2026-11-15_工作区归类\03_工具脚本\organize.py`、`G:\AIrenwu\01_任务归档\2026-11-15_文件夹归类与大纲规矩\03_工具脚本\organize2.py`。
> 回滚：同册 `02_证据日志\搬迁日志.tsv` / `搬迁日志2.tsv` 反向 Move + `整理前备份\` / `整理前备份2\` 镜像覆盖。

## 流程（顺序不可换）

1. 盘点 + 活体排查（见下）；
2. dry-run 出「移动清单 + patch 清单」人工审查；
3. 被 patch 文件原件按相对路径镜像备份；
4. 同一次执行里**先 patch 引用、后搬文件夹**；
5. 守恒断言（根散文件数=允许值 / 根可见文件夹数=大纲类数），不达标即报错停；
6. TSV 清单落盘（源→目标→状态），作为回滚依据。

先 patch 后搬的理由：执行器按**旧路径**盘点枚举与镜像备份，外部引用（手册 md、profile 的 `link:`）同批改完；搬完再 patch 需要重扫新树，且容易漏掉工作区外的引用。

## patch 细节

- **长名优先**排序替换，防前缀吞并；名字边界用 `(?![\w\-])`，避免 `audit-probe2` 命中 `audit-probe20`。
- **双斜杠形式都替换**：`G:\AIrenwu\x` 与 `G:/AIrenwu/x`（pnpm `link:` 用正斜杠）。
- 同目录引用改 `$PSScriptRoot`（含提交信息拼接 `$msg = $PSScriptRoot`），不写死根目录绝对路径。
- 编码自适应：utf8-bom / utf16 / gbk 解码；UTF-8 写回**恒补 BOM**（PS5.1 无 BOM 按 ANSI 读，中文路径乱码），GBK 老脚本保持 ANSI 不动。
  见 [[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]、[[03-通用/03-调试与验证/踩坑-沙箱只放行工作区致写E盘被拒且write会抹掉源码BOM|write 工具抹 BOM]]。

## 证据 integrity 排除（历史快照不改写）

`02_证据日志/`、`tmp/`、`patch-backup/`、`01_会话记录/`、备份夹、`node_modules/`、隐藏目录、回滚工具、历史快照 md/log（如 gemini-pack `0[012]-*.md`、logA/B.txt）。
证据里的旧路径是**历史记录**，不是待修 bug；patch 它们等于伪造取证现场。

## 活体清单（搬前必查）

- `schtasks` 全量 action 路径、HKCU Run、快捷方式目标清单；
- pnpm `link:` 依赖 + `node_modules` 里的 Junction/SymbolicLink（搬源即断链，需重建）；
- 手册 md 的引用、并行会话正在写的目录（看 mtime）。

停→移→恢复：计划任务 Stop → 改 action 路径（管理员令牌创建的任务，改它仍需 UAC 提权）→ Start；断链 Junction 重建；应用占用则停应用→操作→重启。大纲与铁律见 [[规则-工作区大纲与归类铁律]]。

## 验收

- 移动守恒断言通过、locked 清单为空；
- 被 patch 脚本跑自带验证（`verify-optimizations.ps1` → TOTAL FAILURES: 0）；
- git 侧用 rename 检测确认内容未丢（第一轮 71 个 rename），双远端推送后比 HEAD。