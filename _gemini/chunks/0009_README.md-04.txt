实测与判据（2026-11-15）：回收站 52,956 文件 / 21.22 GB 一次清空，全盘合计 +22.42 GB；
`C:\Windows\Logs`、`C:\$SysReset`、`SoftwareDistribution\Download` **非管理员删不掉**，按判据纪律记「失败」不记「已清理」；
还原**目录**必须 `robocopy /E`——`Copy-Item` 不加 `-Recurse` 只建空壳，且目录 `Length` 为 0 会让大小校验误报 PASS。
实测（2026-11-16 第二轮）：回收站又积 8,748 文件 / 2.09 GB → 清空；`%TEMP%` 1,480.8 MB → 73.1 MB；合计 +3.53 GB。
系统目录仍未清（非管理员），改用 `run-system-cleanup.cmd` 双击提权处理，脚本已 DryRun 验证：`Windows\Logs` 可删 221 个 / 27.3 MB。
**坑**：`Get-ChildItem -LiteralPath ... -Recurse -Include *.log` 的 `-Include` **不过滤**（PowerShell 已知行为），
必须改成 `Where-Object { $_.Extension -in '.log', '.etl' }`，否则会连 `.json/.xml` 一起删。

### 工具项目目录（在 `02_项目代码/` 下）
- `dsh-preset-switcher/`：DSH 预设切换器插件（client.js / index.js / 测试；.dsh profile 以 link: 引用，node_modules 内为 Junction）
- `gemini-pack/`：Gemini 双仓数据包构建脚本（`_build_pack.py` 等；快照 .md 不入库）

## 日常用法

> ⚠ **多会话并行警告（2026-11-19）**：`sync-repo.ps1` 内置 `git add -A`，会把**其它会话尚未提交的手册改动**一起卷进提交。
> 多会话共用同一 git 索引时，**改用显式路径暂存**：`git add <只属本会话的路径>` → `git diff --cached --name-only` 核对只含自己的文件 →
> `git commit -F <提交信息>` → `git push gitcode main` + `git push origin main`（失败按 sync-repo 的 per-command 直连回退）→ 跑 `verify-remote-heads.ps1` 校验。
> 单会话、无他人未提交改动时才可直接用 sync-repo.ps1。

```powershell
# 单会话时：新脚本放进 脚本库/<分类>/ 后，用通用同步脚本提交+双推+校验：
powershell -NoProfile -ExecutionPolicy Bypass -File G:\AIrenwu\脚本库\07_机器修复与clash清理\sync-repo.ps1 -MsgFile <提交信息文件路径>
# 多会话时手动（显式路径，勿 add -A）：
git add <本会话的文件路径>
git commit -F <提交信息文件>
git push gitcode main   # 国内直连
git push origin main    # GitHub，走本机 7890 出口（git 全局已配代理；失败时 per-command 直连回退）
```

> **Python 解释器**：正主用 DSH 运行时 `C:\Users\Admin\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe -X utf8`（含 numpy/pandas 等）。
> 本机 `D:\PyCharm\Python\python.exe` 的 console exe 于 2026-11-13 发现消失（`pythonw.exe` 仍在，WindowCenter 用它）；
> 备选 uv 的 `C:\Users\Admin\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe`。`python3` 是坏存根，勿用。
> `.ps1` 必须 UTF-8 BOM+CRLF、`.cmd/.bat` GBK 无 BOM（PS5.1 否则按 GBK 解析报错）。
