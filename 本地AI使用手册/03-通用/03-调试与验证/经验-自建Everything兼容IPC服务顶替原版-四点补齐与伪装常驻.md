---
title: "经验-自建Everything兼容IPC服务顶替原版-四点补齐与伪装常驻"
date: 2026-11-25
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Windows, Python, ctypes, Win32-IPC, Everything]
tags: [Everything, WM_COPYDATA, WM_USER, DeskBox, 全局搜索, 索引, 伪装]
---

# 经验：自建 Everything 兼容 IPC 服务顶替原版（四点补齐与伪装常驻）

## 一句话结论

原版 Everything 不好用、想用自己的索引顶替它时，只要**同时**满足四个条件，调用方（DeskBox、Everything SDK、任意 `FindWindow("EVERYTHING_TASKBAR_NOTIFICATION")` 客户端）就会完全把它当成真 Everything：①窗口类名正确、②`WM_COPYDATA` 回 `LIST/LIST2` 正确、③**`WM_USER` 版本探测必须应答**、④进程名与窗口在客户端探测时已存在。缺第③点是本项目卡了两小时的真正根因。

## 触发条件与影响

- 项目或功能：DeskBox 1.6.0「全局搜索 → Everything 文件搜索」；自建全盘索引（390 万条目）。
- 环境与版本：Windows 11；Python 3.15.2（`D:\PyCharm\Python\python.exe`）；Everything SDK 取自 `https://www.voidtools.com/Everything-SDK.zip`。
- 触发条件：自建 IPC 服务只实现了 `WM_COPYDATA`，未实现 `EVERYTHING_WM_IPC`（= `WM_USER`，0x0400）系列消息。
- 影响范围：DeskBox 日志永远 `everythingMs=0 files=0`，设置页永远显示「未检测到 Everything」；而用 `client_test.py`（只发 COPYDATA）自测**完全正常**，形成「自己测得了、对方用不了」的假象。

## 复现步骤

1. 前置条件：跑起一个只处理 `WM_COPYDATA` 的假 Everything 服务，注册类名 `EVERYTHING_TASKBAR_NOTIFICATION`。
2. 操作或命令：用 Everything SDK 的 `Everything_GetMajorVersion()` / `Everything_IsDBLoaded()` 探测，或直接 `SendMessage(hwnd, WM_USER+0, 0, 0)`。
3. 预期结果：返回 1（主版本号，或「已加载」的真值）。
4. 实际结果：返回 **0**。所有 `WM_USER + n` 都落到 `DefWindowProc` 返回 0。客户端据此判定「Everything 没在运行」。

## 证据

- 服务端日志只有 COPYDATA 记录，没有任何 `WM_USER` 记录。
- Python 探针：修复前 `WM_USER+0 -> 0`、`+3 -> 0`、`+401 -> 0`；修复后 `+0 -> 1`、`+1 -> 4`、`+2 -> 1`、`+3 -> 1357`、`+401 -> 1`、`+402 -> 0`、`+510 -> 1`。
- 修复后 DeskBox 立刻开始查询：
  - 服务端：`QUERY2W q='pdf' flags=0x0 offset=0 max=400 req=0x53` → `-> 400/3048 items in 63.1ms bytes=112284`
  - DeskBox：`[Search] Query completed chars=3 everythingMs=139 deskboxMs=0 totalMs=139 fileOffset=0->400 files=400/3048 visible=404`

## 根因分析

- 已确认的根因：Everything 的 IPC 有两套协议。`WM_COPYDATA` 只负责「查」，`WM_USER + n` 负责「报身份」（版本号、DB 是否加载、是否 NTFS 索引、是否为服务、排序方式等）。客户端**先探测身份再决定发不发查询**。只实现查询、不应答身份，看起来像「窗口存在但进程已死」。
- 排除过的假设：
  - 「DeskBox 需要旁边的 `Everything64.dll` 走 SDK」——`D:\DeskBox` 里根本没有 `Everything*.dll`，它走纯 IPC。
  - 「注册表 `HKCU\SOFTWARE\voidtools\Everything\ExePath` 不对」——改对了也没用。
  - 「进程名不是 `Everything.exe`」——改成 `pythonw.exe` 副本命名 `Everything.exe` 后仍然不行。
  - 「DeskBox 设置里没填程序路径」——填了 `searchEverythingExecutablePath` 仍然不行。
  - 以上全部无效，正是「缺 `WM_USER` 应答」的表现。
- 问题归属：自建实现不完整（本次实现引入）。

## 最小修复

在 `everything_ipc_server.py` 的 `_wndproc` 里，把 `WM_USER` 全部路由到自己的应答函数：

```python
WM_USER = 0x0400

def _wndproc(self, hwnd, msg, wparam, lparam):
    if msg == WM_USER:
        return self._on_ipc(wparam, lparam)
    if msg == WM_COPYDATA:
        return self._on_copydata(wparam, lparam)
    ...

def _on_ipc(self, code, lparam):
    # code 即 WM_USER + n
    table = {
        0: 1,      # MAJOR_VERSION
        1: 4,      # MINOR_VERSION
        2: 1,      # REVISION
        3: 1357,   # BUILD_NUMBER
        5: 1,      # TARGET_MACHINE = x64
        306: 0,    # IS_SERVICE（我们不是服务）
        304: 0,
        400: 1,    # IS_NTFS_DRIVE_INDEXED
        401: 1,    # IS_DB_LOADED
        402: 0,    # IS_DB_BUSY
        403: 0,    # IS_ADMIN
        404: 1,    # IS_APPDATA
        510: 1,    # GET_SORT
    }
    return table.get(code, 0)
```

不影响接口或数据；纯行为补齐。

## 验证记录

- [x] 格式化或静态检查：`python -m py_compile` 通过。
- [x] 类型检查或编译：不适用（Python）。
- [x] 单元、集成或端到端测试：
  - `client_test.py` 自测：`报告` → 174 条 / 60.8ms；`*.pdf` → 1695 条，size/mtime 正确；无结果返回 20 字节空 LIST2 头不卡死。
  - DeskBox 端到端：Alt+D 打开面板 → 输入 `pdf` → `files=400/3048 visible=404`，UIA 读到真实条目（`H:\下载\2025传智教育-寒假师资培训(1).pdf`、`Adobe PDF`、`autofit_pdf.ps1`）。
  - 中文查询：`报告` → `totitems=174`，也正常。
- [x] 构建：不适用。
- [x] 启动或手动回归：杀掉服务后 DeskBox 再查，服务被看门狗拉起后 DeskBox **自动**恢复（不需要重启 DeskBox）——因为 DeskBox 每次打开面板都会重新探测身份。

## 可复用规则

1. **任何「冒充某个软件」的 IPC 服务，先抓它的两套协议**：一套传数据（`WM_COPYDATA` / 命名管道 / COM），一套报身份（`WM_USER+n` / 版本端点 / `IsService`）。只做数据面必然被判「没运行」。
2. **一切 `SendMessage` 到别的进程的测试客户端，发送后必须 Pump 消息**
   （`PeekMessageW + TranslateMessage + DispatchMessageW` 循环），否则对方 `SendMessage(WM_COPYDATA)` 回来时你收不到，表现为「`SendMessage` 返回 1 但一直超时」。
3. **`ctypes` 调 `user32` 必须显式设 `argtypes`**，特别是 `lparam` 要用 `c_ssize_t`，否则 64 位上长指针报 `ArgumentError: int too long to convert`。
4. **`DllImport` 不加 `ExactSpelling=true`** 时，`FindWindowW` 会被解析成 `FindWindowWW`，永远返回 0。PowerShell 里更隐蔽（浏览器找不到，直接给 0）。
5. **开机常驻在没有管理员权限时**：`Register-ScheduledTask` 会 `Access is denied`（0x80070005）。改用「启动文件夹 .vbs + 常驻看门狗进程」：看门狗每 3 秒 `FindWindow` 探测，窗口不在就拉起服务。**且看门狗必须以 `Local\` 前缀命名互斥体**防重复。
6. **VBS 里写中文注释会导致脚本静默不执行**：中文被按 ANSI 写成 `?` 后，若占位改变行边界，后面的 `sh.Run` 会被吞进注释。VBS 内容必须纯 ASCII，用 `[System.Text.Encoding]::ASCII` 写。
7. **`pythonw.exe` 下 `sys.stdout` 是 `None`**，`print` 变成空操作 → 日志空白。要重定向：打开日志文件、`os.dup2` 到 fd 1/2、再把 `sys.stdout` 换掉。

## 适用范围与不适用范围

- 适用：Windows 上用 `ctypes` 自建 Everything 兼容服务；任何需要用「窗口类名 + 消息协议」伪装成一个已有桌面应用的服务。
- 不适用：真的去用 Everything 官方 SDK DLL（那是另一条路，需要 `Everything64.dll` 在旁边）；Linux/macOS；需要进程签名的场景（本方案只伪装名字与协议，不签名）。

## 剩余风险

- 我们应答的是「Everything 1.4.1.1357 x64」的版本号。若某个客户端对更高版本才有的能力（如 1.5 的内容索引）做硬判断，可能仍会走别的分支。
- 假服务的进程名是 `Everything.exe`（`pythonw.exe` 副本），任务管理器里能看到同名的两个进程（原版服务的 `-svc` 实例 + 我们的）。卸载原版 Everything 前要确认它没有开机自启项。
- `WM_USER` 应答表是「够用就好」的近似值，个别客户端可能查更冷门的 code（如 `IS_MATCH_*`），目前统一返回 0；若以后出现某功能不可用，先怀疑这里。

## 关联

- 相关记录：[[踩坑-本机执行环境六个静默陷阱-PS反引号wmic缺失pythonw无stdout]]
- 相关分类：03-调试与验证
- 相关代码与命令：
  - `D:\AI-Tool-State\fullindex\everything_ipc_server.py`（兼容服务）
  - `D:\AI-Tool-State\fullindex\engine.py`（内存索引查询）
  - `D:\AI-Tool-State\fullindex\watchdog.py`（常驻看门狗）
  - `D:\AI-Tool-State\fullindex\client_test.py`（协议测试客户端）
  - `D:\AI-Tool-State\fullindex\sdk\ipc\everything_ipc.h`（权威常量）
