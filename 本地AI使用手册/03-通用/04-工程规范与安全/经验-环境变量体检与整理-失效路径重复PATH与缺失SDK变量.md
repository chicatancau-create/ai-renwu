---
title: "环境变量体检与整理：失效路径、重复 PATH 项、缺失的 SDK/HOME 变量"
date: 2026-11-25
domain: common
category: "04-工程规范与安全"
status: verified
severity: medium
stack: ["Windows 11", "PowerShell 5.1", "注册表 HKCU/HKLM Environment", "JDK 25", "Maven 3.10.0", "Python 3.15.2", "Node 24.15.0", "DevEco Studio", "Android SDK"]
tags: ["环境变量", "PATH", "失效路径", "MAVEN_HOME", "DEVECO_SDK_HOME", "ANDROID_HOME", "python3 存根", "注册表"]
---

# 问题：本机编程类环境变量存在失效路径、重复 PATH 项与关键变量缺失

## 一句话结论

2026-11-25 全量核验 61 个环境变量，发现 **3 个变量指向不存在的路径**（`MAVEN_HOME`、`AQUA_VM_OPTIONS`、`RUSTROVER_VM_OPTIONS`）、**3 条用户 PATH 项冗余/失效**（`C:\node-global` 联接重复、`D:\Git\cmd` 与机器级重复、`C:\Users\Admin\.dotnet\tools` 目录不存在），并**缺失 3 个编程必需变量**（`DEVECO_SDK_HOME`、`ANDROID_HOME`、`ANDROID_SDK_ROOT`）；另发现 `python3` 在本机解析到 0 字节存根（exit 9009）。全部已修复并实测回读，修复后失效路径变量数 = 0。

## 触发条件与影响

- 项目或功能：本机全部编程工具链（Java/Maven、Python、Node、.NET、C/C++、HarmonyOS、Android、Rust/JetBrains 全家桶）
- 环境与版本：Windows 11；PS 5.1.28000.3365；JDK Temurin 25.0.5+8；Maven 3.10.0；Python 3.15.2；Node v24.15.0 / npm 11.12.1；.NET SDK 11.0.100；uv 0.13.8；git 2.55.0
- 触发条件：多次迁移安装目录（C→D）、装/卸 JetBrains 产品、npm 前缀换过
- 影响范围：①`MAVEN_HOME` 失效 → 依赖 `%MAVEN_HOME%` 的脚本/IDE 读到不存在目录；②DevEco 命令行 hvigor 无 `DEVECO_SDK_HOME` → ERROR 00303217；③Android 命令行 adb 需绝对路径；④`python3` 调用失败（exit 9009）

## 复现步骤

1. 前置条件：无
2. 操作或命令：
   ```powershell
   # 逐项核验所有含盘符路径的变量
   foreach($scope in 'Machine','User'){
     $k = Get-Item $(if($scope -eq 'Machine'){'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'}else{'HKCU:\Environment'})
     foreach($n in $k.GetValueNames()){
       $v = $k.GetValue($n)
       if($v -is [string] -and $v -match '^[A-Za-z]:\\' -and -not (Test-Path -LiteralPath $v)){ "$scope / $n = $v" }
     }
   }
   # PATH 存在性 + 重复项
   $all = @(); foreach($s in 'Machine','User'){ foreach($p in ([Environment]::GetEnvironmentVariable('PATH',$s) -split ';')){ if($p.Trim()){ $all += $p.Trim().TrimEnd('\') } } }
   $all | Group-Object | Where-Object Count -gt 1
   ```
3. 预期结果：无输出
4. 实际结果（修复前）：
   - `User / MAVEN_HOME = C:\apache-maven-3.9.16`（实际 Maven 在 `C:\dev\apache-maven-3.10.0`）
   - `User / AQUA_VM_OPTIONS = D:\JAVA\jetbra\vmoptions\aqua.vmoptions`（`D:\JAVA\jetbra` 整个目录不存在）
   - `User / RUSTROVER_VM_OPTIONS = D:\JAVA\jetbra\vmoptions\rustrover.vmoptions`
   - 重复项：`D:\Git\cmd`（机器级 + 用户级各一份）
   - 缺失：`DEVECO_SDK_HOME`、`ANDROID_HOME`、`ANDROID_SDK_ROOT`
   - `python3` → `C:\Users\Admin\AppData\Local\Microsoft\WindowsApps\python3.exe`（**0 字节**，`python3 -V` 返回 exit 9009）

## 证据

- 修复前失效路径扫描（3 条命中，原文见归档备份 `env_snapshot_20261125_144138.csv`）
- `C:\node-global` 是 `D:\node-global` 的 Junction（`Get-Item` LinkType=Junction，Target=D:\node-global），两者在用户 PATH 中相邻出现 → 同一物理目录占两个入口
- `C:\Users\Admin\.dotnet\tools` 不存在，且 `dotnet tool list -g` 输出只有表头（未安装任何全局工具）
- `where python3` → `C:\Users\Admin\AppData\Local\Microsoft\WindowsApps\python3.exe`；`(Get-Item ...).Length` = 0；执行 exit 9009（该存根是"应用执行别名"占位符，未安装商店版 Python）
- NuGet `py -0p` 显示 `-V:3.15 * D:\PyCharm\Python\python.exe`，是唯一注册的默认 CPython

## 根因分析

- 已确认的根因①：`MAVEN_HOME` 是旧版本残留 —— PATH 里用的是 `C:\dev\apache-maven-3.10.0\bin`（3.10.0，能用），但 `MAVEN_HOME` 仍写 `C:\apache-maven-3.9.16`（3.9.16 已删）。两者不同步是因为 Maven 升级时只改了 PATH 没改 `MAVEN_HOME`
- 已确认的根因②：`D:\JAVA\jetbra\vmoptions\*` 是历史批次写入的路径；实际所有 JetBrains 产品（机器级 20 个 `*_VM_OPTIONS`）统一指向 `D:\PyCharm\pojie2099\vmoptions\`。这两条用户级变量是早期遗留，路径从未存在过（该目录创建时间早于目录迁移）
- 已确认的根因③：`C:\node-global` Junction 是 2026-11 迁移时为了兼容 `C:\` 绝对路径建的；迁移完成后 `D:\node-global` 已被写进 PATH，Junction 入口就重复了
- 已确认的根因④：`DEVECO_SDK_HOME` 从未写入环境变量 —— 此前每次 hvigor 命令行构建都是会话内临时 `$env:DEVECO_SDK_HOME=`（见 [[踩坑-DevEco命令行hvigor两坑-缺SDK环境变量报00303217与unsigned警告致假exit1]]），所以换新 shell 就复现 00303217
- 排除过的假设：`vswhere`/`VSINSTALLDIR` 无关（本机未装 Visual Studio）；`HF_HOME`、`UV_CACHE_DIR`、`CODEX_HOME`、`DSH_HOME` 均正常指向 D 盘且目录存在，不是问题
- 问题归属：修改前已有（历史遗留）

## 最小修复

三类改动，全部只动用户级（`HKCU\Environment`），机器级 38 项一字未动：

1. **修正失效路径（3 条）**
   - `MAVEN_HOME`: `C:\apache-maven-3.9.16` → `C:\dev\apache-maven-3.10.0`
   - `AQUA_VM_OPTIONS`: `D:\JAVA\jetbra\vmoptions\aqua.vmoptions` → `D:\PyCharm\pojie2099\vmoptions\aqua.vmoptions`
   - `RUSTROVER_VM_OPTIONS`: `D:\JAVA\jetbra\vmoptions\rustrover.vmoptions` → `D:\PyCharm\pojie2099\vmoptions\rustrover.vmoptions`
   - 全部强制写成 `REG_SZ`（原来是 `REG_EXPAND_SZ`，无用但类型不一致）

2. **清理用户 PATH（24 → 23 项）**
   - 删 `C:\node-global`（`D:\node-global` 的 Junction，重复）
   - 删 `D:\Git\cmd`（机器级已有）
   - 删 `C:\Users\Admin\.dotnet\tools`（目录不存在）
   - 补 `C:\Users\Admin\AppData\Local\Android\Sdk\platform-tools`（前置，adb）
   - 补 `D:\DevEco Studio\sdk\default\openharmony\toolchains`（后置，hdc）

3. **补齐缺失变量（3 条）**
   - `DEVECO_SDK_HOME = D:\DevEco Studio\sdk`
   - `ANDROID_HOME = C:\Users\Admin\AppData\Local\Android\Sdk`
   - `ANDROID_SDK_ROOT = C:\Users\Admin\AppData\Local\Android\Sdk`

4. **`python3` 存根修复**：`Copy-Item D:\PyCharm\Python\python.exe D:\PyCharm\Python\python3.exe`。PATH 中 `D:\PyCharm\Python\` 在 `WindowsApps` 之前，因此 `python3` 现在解析到真解释器（105,696 字节，Python 3.15.2）

改动全部用 `[Environment]::SetEnvironmentVariable(..., 'User')` + `Set-ItemProperty -Type String` 写，最后广播 `WM_SETTINGCHANGE`（`SendMessageTimeout(HWND_BROADCAST, 0x1A, 0, 'Environment', 2, 5000)`）。

## 验证记录

- [x] 格式化或静态检查：修复后全量重扫「含盘符路径且 Test-Path 失败」的变量 → **0 条**
- [x] 类型检查或编译：不适用
- [x] 单元、集成或端到端测试：新建 `$env:Path = 机器PATH + 用户PATH` 后逐个解析 20+ 命令，全部命中预期路径（见下表）
- [x] 构建：不适用
- [x] 启动或手动回归：实测跑通 `adb version`（1.0.41）、`hdc -v`（Ver: 3.2.0f）、`mvn -v`（3.10.0）、`node -v`（v24.15.0）、`python -V`（3.15.2）、`python3 -V`（3.15.2，exit 0）

解析结果复核（新环境）：

| 命令 | 解析到 |
| --- | --- |
| `python` / `python3` | `D:\PyCharm\Python\python.exe` / `D:\PyCharm\Python\python3.exe` |
| `pip` | `D:\PyCharm\Python\Scripts\pip.exe`（pip 26.2.2） |
| `node` / `npm` | `D:\Node.js\node.exe` / `D:\Node.js\npm.ps1` |
| `java` / `javac` | `C:\Program Files\Eclipse Adoptium\jdk-25.0.5.8-hotspot\bin\` |
| `mvn` | `C:\dev\apache-maven-3.10.0\bin\mvn.cmd` |
| `git` | `D:\Git\cmd\git.exe`（2.55.0） |
| `dotnet` | `C:\Program Files\dotnet\dotnet.exe`（11.0.100） |
| `uv` / `uvx` | `D:\uv\bin\`（0.13.8） |
| `adb` | `...\Android\Sdk\platform-tools\adb.exe`（1.0.41） |
| `hdc` | `D:\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe`（3.2.0f） |
| `gh` | `C:\Program Files\GitHub CLI\gh.exe`（2.104.0） |
| `claude` / `codex` | `C:\Users\Admin\AppData\Roaming\npm\*.ps1`（单一健康前缀，无 D:\node-global 遮蔽） |
| `gcc` / `g++` | `C:\dev\mingw64\bin\` |

PATH 长度：机器 690 + 用户 848 = 1,538 字符，远低于 32,767 上限（无截断风险）。

## 可复用规则

1. **环境变量体检的判据只有两条**：①值里含盘符的，逐条 `Test-Path -LiteralPath`；②PATH 合并后 `Group-Object` 找重复。不要只看变量名「像不像」。
2. **Junction 会造成 PATH 重复**：`C:\x` 与 `D:\x` 若为 Junction 关系，PATH 里只该留一个。查法 `(Get-Item C:\x -Force).LinkType -eq 'Junction'`。
3. **同名变量新旧版本并存时要成对检查**：`MAVEN_HOME` 与 PATH 里的 maven bin 必须指向同一版本，否则 `mvn -v` 正常但脚本用 `%MAVEN_HOME%` 就坏。
4. **`python3` 在本机默认坏**：`WindowsApps\python3.exe` 是 0 字节别名存根，exit 9009。要么在 Python 安装目录下放 `python3.exe` 副本（本次做法），要么显式写解释器绝对路径（脚本里的铁律）。
5. **改完必须广播 `WM_SETTINGCHANGE`，但已有进程仍读旧值**：已在跑的终端/IDE/DSH 需重启才见新值。
6. **备份先行**：`reg export "HKCU\Environment" x.reg /y` + 全量 JSON/CSV 快照，改动可逐项回滚。

## 适用范围与不适用范围

- 适用：Windows 10/11 单机、用户级与机器级环境变量、以 C→D 迁移过安装目录的机器
- 不适用：域策略下发（GPO Preferences）托管的环境变量 —— 那种改注册表会被策略覆盖回去；也不适用于多用户共享机器（本次只处理 `HKCU\Environment`）

## 剩余风险

- 本机仍未安装 `pnpm`/`yarn`（只有 corepack 0.34.6）；DSH 插件开发若需 pnpm，要用 `corepack enable pnpm` 或 `npm i -g pnpm`
- `D:\node-global` 仍在 PATH 且其 `npm.cmd`/`npx.cmd` 是旧副本；当前因 `D:\Node.js\` 在机器级 PATH 中靠前而未生效，但若哪天机器级去掉 Node，会回落到这份旧副本
- `VRAY_SEND_ANONYMIZED_FEEDBACK=1` 与 `VRAY_SEND_PERSONALIZED_FEEDBACK=1` 保持原样（未改动：3ds Max 2026 与 V-Ray 仍在装，属用户可选隐私偏好，本次不擅自改）
- `OUR_FREE_MODEL_FREE_TRANSPORT=node`（值为 `node`，非路径）来源不明，未动
- 未安装 Rust 工具链，但用户级与机器级都留着 `RUSTROVER_VM_OPTIONS`；若日后装 RustRover，注意机器级 `*_VM_OPTIONS` 指向 `D:\PyCharm\pojie2099\vmoptions\` 而本次改的用户级指向同一处，已一致

## 关联

- 相关记录：
  - [[踩坑-DevEco命令行hvigor两坑-缺SDK环境变量报00303217与unsigned警告致假exit1]]（`DEVECO_SDK_HOME` 必要性来源）
  - [[踩坑-CCSwitch判claude无法运行且反重力不识别-陈旧npm前缀遮蔽与进程PATH]]（`D:\node-global` 与 `C:\node-global` Junction 的来历）
  - [[踩坑-本机执行环境六个静默陷阱-PS反引号wmic缺失pythonw无stdout]]（`python3` 坏存根、`uv.exe` 丢失但变量还在）
  - [[经验-AppData缓存迁D盘复用DSH-Guard核心按组包装]]（`AppData\Roaming\npm` 是活前缀、`UV_CACHE_DIR`/`HF_HOME` 已在 D 盘）
- 相关分类：`03-通用\04-工程规范与安全`、`03-通用\03-调试与验证`
- 相关代码、命令或文档：归档 `G:\AIrenwu\01_任务归档\2026-11-25_环境变量体检与整理\`（`01_报告\环境变量体检与整理报告.md`；`02_备份\`：`HKCU_Environment_*.reg`、`HKLM_Environment_*.reg`、`env_snapshot_*.json`、`env_snapshot_*.csv`、三个 fix 脚本）
