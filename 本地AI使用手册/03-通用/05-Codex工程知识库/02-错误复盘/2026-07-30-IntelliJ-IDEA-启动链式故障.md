---
date: 2026-07-30
project: "IntelliJ IDEA 本地安装"
stack: [Windows, IntelliJ IDEA, JetBrains Runtime, Java]
status: verified
tags: [engineering-retrospective]
---

# 错误：IntelliJ IDEA 因 Java Agent 与文件 ACL 异常连续启动失败

## 背景、复现与影响

Windows 上的 IntelliJ IDEA 2026.2 无法从桌面快捷方式启动。故障发生在本地 IDE 安装和用户级 JVM 启动配置，不涉及业务项目代码。

### 复现步骤

1. 前置条件：用户级 `IDEA_VM_OPTIONS` 指向自定义 VM 参数文件，安装目录中部分文件关闭了 NTFS 权限继承。
2. 操作或命令：启动 `idea64.exe`；随后使用 `idea.bat` 捕获控制台错误，并使用最小 AWT 字体探针隔离 JBR 字体初始化。
3. 预期结果：IDEA 打开欢迎界面并保持运行。
4. 实际结果：先在处理 `-javaagent` 时发生 JVM 原生崩溃；移除代理后依次出现 JAR 读取拒绝和字体配置初始化失败。

## 现象与证据

- 启动对话框：`processing of -javaagent failed, processJavaStart failed`。
- JVM 崩溃日志的实际命令行包含第三方 `-javaagent:<REDACTED>=jetbrains`。
- `idea.bat` 报告 `java.nio.file.AccessDeniedException`，目标为安装目录内的 JAR。
- 全安装目录可读性扫描：3395 个文件中有 50 个无法读取；这些文件的 ACL 关闭继承，缺少普通用户的读取执行权限。
- 最小 AWT 探针报告 `Fontconfig head is null`，对应的 JBR `fontconfig.bfc` 也在不可读文件清单内。

## 问题归属判断

- [x] 修改前已有问题
- [ ] 本次修改引入的问题
- [x] 环境、依赖或外部服务问题
- 判断依据：首次诊断前即可稳定复现；故障来自用户级第三方 JVM 代理配置及本地安装文件的 NTFS ACL，不来自项目代码。

## 根因

1. 用户级 `IDEA_VM_OPTIONS` 加载了第三方 Java Agent。该代理无法兼容 IDEA 2026.2 随附的 JBR 25，导致 JVM 在 `processJavaStart` 阶段原生崩溃。
2. 安装目录中 50 个文件被设置为受保护 ACL，只允许 SYSTEM、管理员组和一个显式 SID，普通桌面进程无法读取。最先阻断启动的是平台 JAR；修复后，JBR 字体配置文件继续阻断 UI 初始化。
3. 原始启动方式仅显示首个启动错误，后续权限问题被前置的 Java Agent 崩溃遮蔽，因此必须逐层修复并重新启动验证。

## 最小修复

- 为三个自定义 JetBrains VM 参数文件创建带时间戳的备份，仅删除 `-javaagent` 行，保留其他 JVM 参数。
- 对全安装目录进行只读扫描，仅对确认无法读取的 50 个文件执行管理员接管、启用父目录权限继承和 ACL 重置；未改动文件内容。

## 验证记录

- [通过] `java.exe -version` — JBR 25.0.3 正常退出，退出码 0。
- [先失败，修复后通过] 全安装目录文件只读扫描 — 修复前 3395 个文件中 50 个读取失败；修复后失败数为 0。
- [先失败，修复后通过] 最小 AWT 字体探针 — 修复前 `Fontconfig head is null`；修复后识别 160 个字体族，退出码 0。
- [先失败，修复后通过] `idea64.exe` 启动 — 最初 JVM 原生崩溃，之后暴露 JAR 和字体配置读取失败；最终进程持续运行超过 30 秒并进入 `IDE STARTED`。
- [通过] IDEA 延迟健康检查 — 进程响应正常，窗口标题为“欢迎访问 IntelliJ IDEA”，本次启动日志的已筛选严重错误数为 0，未新增 JVM 崩溃日志。
- [未执行] 业务项目编译与测试 — 本任务不涉及具体项目，也未提供需要验证的业务工程。

## 预防规则

- IDEA 升级 JBR 主版本后，如存在自定义 `IDEA_VM_OPTIONS`，先检查并隔离第三方 `-javaagent`，再判断 IDE 安装损坏。
- Windows 上遇到 `AccessDeniedException` 或字体配置初始化失败时，应对安装目录做实际文件打开测试；仅查看文件存在性或目录 ACL 不足以证明文件可读。
- 若多个离散安装文件关闭继承，应先生成精确失败清单，只修复已确认异常的 ACL，并在修复后全量复扫。
- 适用范围：Windows 本地 JetBrains IDE 安装的启动故障。若文件内容校验失败、磁盘损坏或安装包缺失，不能用 ACL 修复代替文件恢复。

## 剩余风险

- 未验证第三方 Java Agent 的替代版本；继续使用该代理可能再次导致升级后的 JBR 崩溃。
- 未执行官方安装包哈希或签名清单级完整性比对；已验证的是全部现有安装文件可读和 IDE 实际启动成功。

## 关联

- 项目：IntelliJ IDEA 本地安装
- 相关模式：无
- 相关提交或文件：用户级 VM 参数、IDE 安装目录 ACL
