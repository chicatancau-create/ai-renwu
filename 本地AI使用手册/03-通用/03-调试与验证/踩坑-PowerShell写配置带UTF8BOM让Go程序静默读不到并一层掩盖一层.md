---
title: "PowerShell 写配置带 UTF-8 BOM 让 Go 程序静默读不到，还会一层挡一层掩盖真错误"
date: 2026-11-15
domain: common
category: "调试与验证"
status: verified
severity: high
stack: ["Windows PowerShell 5.1", "Go encoding/json", "牧羊人 Herdsman", "Windows 11"]
tags: ["BOM", "UTF-8", "PowerShell", "Go", "配置读写", "静默失败", "错误掩盖", "编码"]
---

# 问题：改完配置文件，应用说「解析失败」；把 BOM 去掉后又冒出第二个错

> 复现、定位、修复、验证全部完成，见「验证记录」。

## 一句话结论

**Go 的 `encoding/json` 不接受 UTF-8 BOM**，而 PowerShell 的 `Set-Content`/`Out-File`/`>`
默认会给文件加 BOM（或按 GBK 写中文）。后果不是报错退出，而是**静默读不到这份配置**，
表现得像应用坏了。更要命的是：**BOM 会挡住后面的错误**——去掉 BOM 才露出第二层 bug，
而「错误文案变了」很容易被当成「已经修好了」。

## 触发条件与影响

- 项目或功能：手工编辑 Go 编写的本地应用（牧羊人 Herdsman）的 JSON 配置
- 环境与版本：Windows 11 + PowerShell 5.1 + Go 应用（encoding/json）
- 触发条件：用 PowerShell 重写 `registry\local_models.json`、`startup_state.json`
- 影响范围（本机全部实际发生过）：
  - `load local model registry failed` → 模型注册表读不出来 → **界面上长出幽灵重复项**
  - `read last active model state failed` → **「开机自动恢复上次模型」一直不生效**
  - `Failed to snapshot main chat model before shutdown` → 退出时状态存不下
  - 上一任因此把幽灵重复项误判成应用 bug，反复删除重建模型卡片

## 复现步骤

1. 前置条件：任意 Go 应用，配置是 UTF-8 无 BOM 的 JSON
2. 操作或命令：
   ```powershell
   (Get-Content x.json -Raw) -replace 'a','b' | Set-Content x.json   # 默认编码
   ```
3. 预期结果：应用正常读到新配置
4. 实际结果：应用日志立刻出现
   ```
   level=WARN msg="load local model registry failed"
     error="unmarshal local model registry: invalid character 'ï' looking for beginning of value"
   ```
   报错里的 `ï` 就是 BOM 三字节 `EF BB BF` 被当普通字节读的第一个字符——**这条报错可以直接当特征码用**。

## 证据

同一文件先后两阶段的日志（本机实测，同一台机器、同一个应用）：

```
10:43–17:21  invalid character 'ï' looking for beginning of value        ← BOM 层
17:25 之后   json: cannot unmarshal string into Go struct field
             Record.display_name of type map[string]string                ← 第二层
```

- 第一层：`HK...registry\local_models.json` 前 3 字节确认为 `EF BB BF`
- 第二层：同一文件的 `display_name` 被上一任写成了**字符串**，
  而 Go 结构体要 `map[string]string`（即 `{"en":..,"zh":..}`）。
  **这个错误一直都在，只是被 BOM 挡在后面从来没机会暴露。**
- 内容本身没问题：文件里的中文用 UTF-8 解码完全正确，
  控制台显示乱码只是终端代码页（GBK）渲染问题——不要因为看到乱码就去改文件编码。
- 反证「manifest 里的 display_name 是有效的」：改完两层错误清零后，
  界面显示名仍然是错的，最终查明**显示名取的是 GGUF 文件自己的 `general.name`**，
  应用根本不读 manifest/registry 的 `display_name`（属于另一个坑，见「剩余风险」）。

## 根因分析

- 已确认的根因：
  1. PowerShell 5.1 的默认输出编码会给 UTF-8 加 BOM；`>` 重定向还可能按 ANSI/GBK 写中文。
  2. Go `encoding/json` 不做 BOM 剥离，解析在第一个字节就失败。
  3. 应用对「配置读不到」只打 WARN 并**继续用空状态启动**，所以表现为静默降级而不是崩溃。
- 排除过的假设：文件内容真的坏了（UTF-8 解码正常，排除）；应用版本 bug（同版本读无 BOM 文件正常，排除）
- 问题归属：**本次修改引入**（用 PowerShell 改配置文件这一步）

## 最小修复

1. 写这台机器上任何供第三方应用读的 json/yaml/toml，一律显式 UTF-8 **无 BOM**：
   ```python
   open(p,'wb').write(json.dumps(d, ensure_ascii=False, indent=4).encode('utf-8'))
   ```
   或用编辑器「另存为 → UTF-8（不是「带 BOM 的 UTF-8」）」。
2. 改完**必须验首字节**，别只看内容对不对：
   ```bash
   head -c 3 文件 | xxd      # 出现 efbbbf 就是写坏了
   ```
3. 第二层同类坑的修法：字段类型要跟结构体一致——`display_name` 写成
   `{"en": "...", "zh": "..."}`，不能是裸字符串。

## 验证记录

- [x] 复现：BOM 文件 → 日志报 `invalid character 'ï'`；去 BOM → 该条消失并暴露下一层类型错误
- [x] 修复：两个文件重写为无 BOM + `display_name` 改 map 形式
- [x] 验证：重启应用后，`invalid character` 与 `cannot unmarshal` **两类错误计数都归零**
  （不是「文案变了」，是日志里彻底不再出现）
- [x] 副作用验证：开机自动恢复模型从此生效（之前一直不生效）；幽灵重复项不再产生
- [x] 扫描全量：把应用配置目录整个扫一遍找 BOM，共命中 2 个文件并全部修掉

## 可复用规则

**修完一个报错，判定标准是「这条日志在新一轮运行里不再出现」，不是「错误信息变了」。**
错误文案变化往往只意味着「挡住了下一层错误」。

配套两条硬规则：
1. 在这台 Windows 上改任何应用配置文件前，先 `head -c 3` 看原文件有没有 BOM；
   写完再看一次，**保持与原文件一致**（原文件有 BOM 的，应用大概率也读不了它——
   那说明 BOM 本身就是上一个受害者留下的）。
2. 见到日志里 `invalid character 'ï'`＝**立刻想到 BOM**，不要去查应用逻辑。

## 适用范围与不适用范围

- 适用：本机一切 Go（`encoding/json`）编写的 CLI/桌面应用的 JSON/YAML 配置；
  PowerShell 参与的任意配置改写；日志里出现 `ï`、`锟斤拷`、乱码型解析错误
- 不适用：Node/Python 的 json 解析器能容忍 BOM，不会复现此症状；
  本条也不适用于 `.ps1` 需要「UTF-8 **带** BOM」的反向要求（PowerShell 5.1 读无 BOM 的
  UTF-8 脚本会把中文读成乱码，见 [[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]）
  —— **两者方向相反，别记混**：给 PowerShell 的脚本要带 BOM，给 Go 的配置不能有 BOM

## 剩余风险

- 这次没解决的相邻坑（同一应用，独立一条）：界面上的**显示名取的是模型文件自己的
  GGUF 元数据 `general.name`**，改 manifest / registry 的 `display_name` 完全无效。
  判据：同机另一个模型的 GGUF 里 `general.name` 是正常名字，它显示就正常。
- 应用配置目录里同名文件（manifest / launch_config / launch_records 下同名 json）
  做备份时会互相覆盖，备份文件名要把目录编码进去。

## 关联

- 相关记录：[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]（方向相反的 BOM 规则）、
  [[踩坑-GetContent默认按代码页解码致UTF8中文回显乱码]]、
  [[踩坑-沙箱只放行工作区致写E盘被拒且write会抹掉源码BOM]]、
  [[踩坑-本机执行环境六个静默陷阱-PS反引号wmic缺失pythonw无stdout]]、
  [[规则-清理归档前先反查三类引用]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]、[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关文档：`D:\Models\Ternary-Bonsai-2-27B-gguf\部署交接说明.txt` 第三、九节
