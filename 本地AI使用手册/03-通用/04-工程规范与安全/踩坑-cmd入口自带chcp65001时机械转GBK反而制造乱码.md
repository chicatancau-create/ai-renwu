---
title: "踩坑：.cmd/.bat 自带 chcp 65001 时，按「GBK 无 BOM」铁律机械转码反而把原本正常的脚本改坏"
date: 2026-11-26
domain: common
category: 04-工程规范与安全
status: verified
severity: medium
stack: [Windows, cmd, PowerShell 5.1, Python]
tags: [chcp 65001, 代码页, GBK, BOM, 编码纪律, 批量改写, 自引入回归]
---

# 问题：按编码铁律批量修 .cmd/.bat，把 4 个自带 `chcp 65001` 的脚本改花了

## 一句话结论

本机纪律是「`.ps1` 必须 UTF-8 BOM + CRLF、`.cmd/.bat` GBK 无 BOM」。但**脚本自身若在第 2 行写了 `chcp 65001`，它已经声明要 UTF-8 控制台**，这时把它机械转成 GBK，控制台里中文反而变乱码——**脚本自身的代码页声明优先于全局编码铁律**，批量修必须加守卫跳过。

## 触发条件与影响

- 项目或功能：`G:\AIrenwu` 全库编码纪律整治（2026-11-26）
- 环境与版本：Windows + PowerShell 5.1（没有 pwsh 时也可用 `C:\Program Files\PowerShell\7\pwsh.exe`）
- 触发条件：脚本里既有中文、又有 `chcp 65001`（或 `chcp65001`），且没带 BOM / 能按 GBK 解码
- 影响范围：`01_任务归档\2026-11-01_CCSwitch接入WorkBuddy密钥\03_工具脚本\` 下 4 个 `.bat`
  （`一键接入.bat` / `停止转发.bat` / `启动转发.bat` / `回滚.bat`）被错误转成 GBK，控制台输出反成乱码

## 复现步骤

1. 前置条件：准备一个含中文、带 `chcp 65001 >nul`、内容为 UTF-8 无 BOM 的 `.bat`
2. 操作或命令：按「.cmd/.bat 必须 GBK 无 BOM」的规则把它转成 GBK
3. 预期结果：控制台中文正常
4. 实际结果：**控制台中文变乱码**——`chcp 65001` 让 cmd 按 UTF-8 解释输出，而文件内容已经是 GBK 字节

## 证据

修完第 1 批后复测发现 4 个 `.bat` 输出异常，从备份逐字节还原后 sha256 前 16 位全部与原件一致：

```
一键接入.bat   706B  198C6D7953DF39A7   与原件一致=True
停止转发.bat   595B  BFA1859F9B9B7C22   与原件一致=True
启动转发.bat   613B  4931B80826D2A63B   与原件一致=True
回滚.bat       647B  A8D88F83FFFA34EF   与原件一致=True
```

全库扫出的 7 个自带 `chcp 65001` 的 `.cmd/.bat`（登记为**合规例外**，不再动）：

```
01_任务归档\2026-11-01_CCSwitch接入WorkBuddy密钥\03_工具脚本\  一键接入.bat / 停止转发.bat / 启动转发.bat / 回滚.bat
01_任务归档\2026-11-01_DeepSeek客户端接入WorkBuddy密钥\03_工具脚本\  rollback.bat
01_任务归档\2026-11-01_任务栏透明软件隐藏\03_工具脚本\  restore-tray.bat
01_任务归档\2026-11-11_OpenRevo电池限充\03_工具脚本\  RUN-AS-ADMIN.cmd
```

## 根因分析

- 已确认的根因：`.bat` 的显示编码由**运行时 `chcp`** 决定，不由文件字节单独决定。文件写 GBK 字节 + 控制台声明 UTF-8 = 必花。
- 排除过的假设：
  - 「GBK 本身就是 .cmd 的约定，转了总是对的」——错，`chcp` 覆盖了约定。
  - 「是 PS 5.1 读文件时解码坏了」——不是，这次出错在 cmd 运行时按代码页解释输出，跟 PS 无关。
- 问题归属：本次修改引入（我自己的批量脚本引入的回归）

## 最小修复

在批量脚本里加守卫函数，对 gbk / utf-8 两种解码结果**都**检查声明串，命中就整个跳过：

```python
def declares_utf8_codepage(raw: bytes) -> bool:
    for enc in ("gbk", "utf-8"):
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        low = t.lower()
        if "chcp 65001" in low or "chcp65001" in low:
            return True
    return False
```

命中该函数的文件 `return None`，不产生任何写入计划。改完后复扫预演结果 `变更条目: 0`。

## 验证记录

- [x] 格式化或静态检查：`[System.Management.Automation.Language.Parser]::ParseFile` 抽验 4 个代表 `.ps1` 全部 `[OK]`
- [x] 类型检查或编译：不适用（脚本）
- [x] 单元、集成或端到端测试：批量脚本 `--dry` 复扫 → `预演 变更条目: 0`
- [x] 构建：不适用
- [x] 启动或手动回归：4 个 `.bat` 逐字节还原并 sha256 比对 `与原件一致=True`

## 可复用规则

1. **文件编码 + 运行时代码页是一对**：改 `.cmd/.bat` 编码前先看它有没有 `chcp`，有就按它声明的来，别按铁律机械改。
2. **批量转码脚本必须内置「自身声明优先」守卫**，且守卫要对多种解码结果都试一遍（文件本身可能是 GBK 也可能是 UTF-8）。
3. **收窄改动范围**：一开始按铁律严跑预演过 **205 项变更**，其中约 175 项只是纯 LF→CRLF 归一化，在 git 白名单目录里会造出上百个无实质意义 diff。真正会引发乱码的只有两类：`.ps1` 含中文无 BOM、`.cmd/.bat` 带 BOM 或不能按 GBK 解码。**只修这两类**。
4. 批量改完必须**逐字节与备份比对**，别信「脚本跑完了就是对的」。

## 适用范围与不适用范围

- 适用：任何「有全局编码铁律 + 脚本自带代码页声明」的批量修整场景；Windows 批处理与 PS 混用目录
- 不适用：脚本里没有 `chcp` 声明；纯 ASCII 脚本；不以控制台输出为交付物的脚本（如仅被程序调用的 `.bat`）

## 剩余风险

- 全库仍有 19 个「非 UTF-8 文本」（`.log` 10 / `.txt` 9 / `.xml` 2 等）未统一，它们是 GBK 编码的历史日志，本身不是错误，但也意味着用 UTF-8 编辑器打开会花。
- `.ps1` 换行仍是 LF 未统一到 CRLF（有意放弃，避免造无意义 diff）；若将来某脚本被 PS 5.1 以外环境按 CRLF 严格解析，需单独处理。

## 关联

- 相关记录：[[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]（同族：`.ps1` 缺 BOM 被按 GBK 解释）、
  [[踩坑-GetContent默认按代码页解码致UTF8中文回显乱码]]（同族：出错在「读」而不是「写」）
- 相关分类：[[03-通用/04-工程规范与安全/README|工程规范与安全]]
- 相关代码、命令或文档：`G:\AIrenwu\01_任务归档\2026-11-26_AI任务区乱码与形态整治\03_工具脚本\fix_encoding.py`、
  `fix_encoding_manifest.tsv`（30 条落笔清单）；铁律原文见 `G:\AIrenwu\README.md:227`
