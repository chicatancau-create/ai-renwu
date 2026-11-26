# 经验-LightC 全模块 UIA 驱动清理与社交默认全选误删用户数据

- 状态：verified
- 日期：2026-11-24
- 分类：03-通用/03-调试与验证
- 严重度：high（含一次真实用户数据误删）
- 关联归档：`G:\AIrenwu\01_任务归档\2026-11-24_LightC全功能扫描与垃圾判定\`（报告 + 控件树证据 + 脚本）

## 症状

- 想用程序化方式驱动 LightC（Tauri v2.19.0，`D:\LightC\LightC.exe`）跑全部扫描并取结构化结果；设 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222` 重启后端口**不监听**。
- 用 UIA 勾选清理时，勾选"看起来点了"但工具栏计数不变；社交模块一次清理把**微信传输文件/图片视频/收藏**等用户数据永久删除（4.59 GB，回收站 0 条）。

## 根因

1. **CDP 环境变量被 Tauri 覆盖**：Tauri 自己向 WebView2 传 `AdditionalBrowserArguments`（`--disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection` 等），WebView2 因此**忽略**环境变量注入的浏览器参数。提权 dump `Win32_Process` 命令行可证实 msedgewebview2 浏览器进程没有 `--remote-debugging-port`。⇒ Tauri 应用想开调试口不能靠环境变量，改走 UIA。
2. **各模块选择控件形态不同**，一套定位逻辑不能通用：
   - 垃圾清理：行 = `cursor-pointer`+`px-5` 的 Group；复选框 class 为空，靠**尺寸 14–32px** 命中。
   - 残留&缓存：行 = `cursor-pointer`+`p-4 rounded-xl`，**行内无复选框**，选中 = 点击行本身。
   - 旧驱动：真 `ControlType.CheckBox`（Name 含 inf+详情），用 `TogglePattern`。
   - 外壳图标：无复选框，每行独立按钮 `移除入口`/`彻底删除`。
   - 确认弹窗按钮常与工具栏**同名**（清理/删除选中）⇒ 确认要**反向**找最后一个匹配按钮。
3. **勾选状态跨导航保留**：模块间切换不清空选择；"ToggleOff 用户数据"会把默认未选的分类反向打开。社交模块**默认全选 8190（含用户数据三类）**，一旦取消勾选未生效就按默认全选执行 ⇒ 误删。
4. 工具栏计数格式不统一：`清理 (N)` / `清理 N` / `已选 N 项，共 X B` / `删除选中 (N)`，等待与守卫正则必须全覆盖，否则空等 180s 或守卫失效。
5. LightC 界面"C 盘剩余"是**启动时缓存的陈旧值**（实测界面 114.17 GB 而真实 137→147 GB）；判释放量一律用 `Get-PSDrive` / 目标 du 前后差。
6. 旧驱动删除前 LightC **强制同体积备份**（5.94 GB）⇒ 净释放 0，清理旧驱动不等于省空间。

## 修复 / 对策

- 放弃 CDP，用**同管理员级别 UI Automation**（`UIAutomationClient`）后台读树+Invoke/Toggle，不抢前台不置顶。
- 清理脚本加**硬守卫**：`-ExpectMin N`，勾选后计数不足 N 就 ABORT 不点清理；状态感知勾选（checked = class 含 `bg-[var(--brand-green)]`，只在状态不符时点）。
- 社交/任何含用户数据的模块：**先 dry-run（-NoClean）核对工具栏计数与分类**，确认只含缓存类才真清；默认全选≠安全。
- 提权 launcher 用 `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Verb RunAs`（`pwsh` 名字找不到），**不要 -Wait**（会等整棵子进程树含目标应用；kill launcher 会连带杀应用）。
- 含中文 .ps1 必须 UTF-8 BOM+CRLF；**edit 工具会抹掉 BOM**，每次 edit 后重加 BOM 再跑，否则 PS5.1 按 ANSI 读中文秒退。

## 实际验证

- 13 模块全部扫描成功并落控件树 TSV；垃圾十分类全选清 63282 成功 / 5.54 GB；AI 工具 75 目录 ≈1.28 GB；右键 6 无效项（.reg 自动备份于 `C:\Users\Admin\AppData\Local\LightC\data\reg_backups\`）；残留 25 空壳目录 `Test-Path`=False；夸克外壳入口注册表键已不存在。
- 误删事故已复核日志 `cleanup_20261124_162138.json`：8190 条 / 8187 成功 / 4.59 GB，含 `E:\微信聊天文件\xwechat_files\wxid_hv1i7l8cyl6p22_5f9b\msg\file` 97 个 3188.53 MB 等；回收站枚举 0 ⇒ 永久删除。

## 适用范围与剩余风险

- 适用：LightC / 同类 Tauri+WebView2 清理软件的程序化驱动与垃圾判定。
- 剩余风险：微信 `msg\file` 旧文件（2026-10）服务器大概率已过期**不可恢复**；图片/视频/收藏或可重拉。QQ nt_data 多为可再下载资源。
- 判定铁律复用：应用状态层（profile/User Data/EBWebView）与在装程序本体**只报告不删**；判删两条件 = 内容可证明无 + 位置属可丢弃层；清理前反查计划任务/Run 自启/脚本文档引用。

## 2026-11-24 后续（verified，17:29–18:15）

- 用户明确不需要回滚后，旧驱动可真正省空间：先让 LightC「备份并删除」10 高置信包（备份落 `C:\Users\Admin\AppData\Local\LightC\data\driver_backups`，644 文件 5.94 GB），再按授权删备份目录；`pnputil /enum-drivers` 复验 10 个 oem*.inf 全消失，C 盘净 +4.61 GB。**备份不删则净释放 0** 的结论只在"保留回滚"前提下成立。
- UIA 虚拟列表两坑：①offscreen 行的 CheckBox `Toggle()` 不生效 → 先 `ScrollItemPattern.ScrollIntoView()` 再切；②`ToggleState` 读数陈旧不可信 → 以**工具栏计数增量**为真值，切换后计数没涨就再切一次。
- **并发双 UIA 实例会互相 double-toggle**（计数 4/6 振荡）；`-ExpectMin` 守卫三次正确 ABORT 未误清。驱动类清理链必须单实例跑。
- 启动竞态：LightC 刚启动 12s 内 sidebar 未就绪 → `nav index out of range`；链脚本应先等窗口/侧边栏就绪再扫描。
