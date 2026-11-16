---
title: "NVMe 异常断电导致 git loose object 损坏（inflate 失败），内容不可恢复，只能重建历史"
date: 2026-10-13
domain: common
category: 调试与验证
status: verified
severity: high
stack: [git, Windows, NVMe, 断电恢复]
tags: [数据损坏, 取证, 备份, 历史重建]
---

# 问题：仓库文件还在、目录树正常，但 `git show` / `git diff --cached` / `git reset` 一律报 `inflate: data stream error`

> 2026-10-13 在 `E:\fullstack-code` 实际处置；2026-11-15 回写手册。

## 一句话结论

无 DRAM 缓存的 NVMe 在异常断电后会出现「**目录项与文件尺寸落了盘、数据页没落盘**」：
文件大小正常、mtime 正常，但内容全是 `0x00`。git 的 loose object 同样中招，且 **zlib 流已毁 = 内容不可恢复**。
此时**任何"保留旧提交"的修补方案都会让 `git fsck` 永久报错**，唯一干净的修法是**备份后重建历史**。

## 触发条件与影响

- 项目或功能：`E:\fullstack-code` 学习仓库（2 次提交，无远程）
- 环境与版本：Windows 11；git 2.55.0.windows.3；YMTC PC41Q-1TB-B（无 DRAM 缓存），E/F/G 三个分区同盘
- 触发条件：近 30 天 9 次 `Kernel-Power 41` 非正常关机
- 影响范围：4787 个文件中 715 个整文件全零；`.git` 的 index + 7 个 loose object；`Python/.venv` 764 个里 658 个（86%）

## 复现步骤

1. 前置条件：仓库经历过异常断电，且盘上存在未落盘的数据页
2. 操作或命令：
   ```bash
   git fsck --full
   git show HEAD:README.md
   ```
3. 预期结果：正常列出对象 / 打印文件内容
4. 实际结果：
   ```
   error: inflate: data stream error (unknown compression method)
   error: unable to unpack a6be4cfc... header
   fatal: loose object a6be4cfc... is corrupt
   ```

## 证据

- `git fsck --full` 输出 7 个 `object corrupt or missing`，另有 `dangling tree` / `missing blob`
- 损坏对象**尺寸非零**（674 ~ 19662 字节），但内容全零 → 不是"文件被删"，是"数据页没写"
- 顺带发现 `.git/COMMIT_EDITMSG` 变成 2299 字节**全空格**，同属该事件的痕迹
- 对照项：`chkdsk E: /scan` 未发现一致性问题、坏扇区 0 KB、盘体 Wear=0 ⇒ **文件系统层面无错，坏的是数据本身**

### 把损坏对象映射回文件路径（关键取证动作）

`git fsck` 只给哈希，不给路径。要判断"丢了什么"必须反查：

```bash
git ls-tree -r HEAD | grep -E 'a6be4cfc|df36fcfb|1635963f|4461e111|6183b501|804938ae|e2a7b7f7'
```

实测映射结果：

| 对象 | HEAD 中的路径 |
|---|---|
| `a6be4cfc` | `README.md` |
| `4461e111` | `Web/js自学/javaScript基础语法.html` |
| `6183b501` | `Web/js自学/循环与数组.html` |
| `1635963f` | `Web/vue/package-lock.json` |
| `df36fcfb` | `Web/vue/public/favicon.ico` |
| `e2a7b7f7` | `progress.md` |
| `804938ae` | dangling（更早的 progress.md，不在当前 HEAD） |

> 注意：`git ls-tree` 对中文路径默认输出八进制转义串，比对前先处理（见 [[踩坑-ls-tree名字输出八进制转义致中文路径比对全错]]）。

## 根因分析

- 已确认的根因：无 DRAM 缓存的 NVMe + 频繁异常断电 ⇒ 元数据已提交、数据页未提交
- 排除过的假设：
  - "文件被误删/被清空"——尺寸与 mtime 均正常，否
  - "git 版本 bug"——换 `git cat-file` 同样 inflate 失败，否
  - "磁盘有坏道"——chkdsk 与 Wear 均正常，否
- 问题归属：环境或硬件（非本次修改引入）

## 最小修复

**无法修复原对象**，只能止损重建：

1. 备份先行：`tar -czf .workbuddy-ai/backup/dotgit-<日期>.tar.gz .git`，并把 `git log` / `git ls-tree -r HEAD` / `git reflog` 存成文本（损坏后这些元信息仍可读，是最后的历史线索）
2. `mv .git <备份目录>` → `git init -b main` → `git add -A` → 一次性提交当前工作区
3. 推送新建的私有远程仓库，形成第二份副本

**为什么不能用 `git hash-object -w` 回填**：loose object 按内容寻址，只有**逐字节相同**的原始内容才能得到原哈希；内容已丢，哈希永远凑不回来。

**为什么不在旧提交上叠加新提交**：损坏 blob 仍被祖先提交引用，`fsck` 会继续报错，`git checkout <旧提交>` 依旧中断。

## 验证记录

- [x] 仓库健康：`git fsck --full` 重建后**零输出**
- [x] 历史可读：`git log --oneline` 正常；`git show HEAD:README.md` 正常打印
- [x] 同步：`git rev-parse HEAD` == `git rev-parse origin/main`
- [x] 敏感项：`git ls-files | grep -Ei 'local.properties|\.env$|secret|token|\.pem$|\.key$'` 无输出
- [ ] 构建验证：当时未做（后于同日补跑 `npm run build` 通过，vite 8.3.4，142ms）

## 可复用规则

1. **怀疑零填充时数非零字节，绝不看 mtime / 文件大小**——本次 715 个坏文件的 mtime 和尺寸全都正常。
   ```python
   data = open(p, 'rb').read()
   if data and not any(data):   # 整文件全 0x00
       ...                      # 0 字节文件要单独分支，别混进"损坏"
   ```
   注意 **0 字节 ≠ 损坏**：pip 的 `__init__.py` / `py.typed` / `REQUESTED` 本来就该是空的，要剔除避免误报。
2. **先备份整个 `.git` 再谈修复**，并把 `git log`/`ls-tree`/`reflog` 存成纯文本——对象坏了之后这些仍可读。
3. **损坏对象 → 路径的映射必须做**，否则无法判断损失范围，也无法决定"哪些文件要重写、哪些能从别处捞回"。
4. **重建历史前必须确认不再需要旧版本**，并在项目文档里记下被丢弃的提交哈希。
5. 重建后立刻建远程副本；**同一块 NVMe 上的"备份"不防断电**，只防误操作。

## 适用范围与不适用范围

- 适用：异常断电/蓝屏后 git 报 inflate 错误、文件内容全零、`.git` 对象损坏；也适用于 `node_modules` / `.venv` 大面积损坏后的清理重建
- 不适用：对象仍在 pack 里且 pack 未损坏（可尝试从 pack 恢复）；有可用远程/备份时（优先从远端 `clone` 恢复，而不是重建历史）

## 剩余风险

- 原 2 次提交的内容永久丢失，只剩提交信息文本
- 单盘多分区意味着"换分区备份"不防此类故障；需跨物理盘或远程

## 关联

- 相关记录：[[踩坑-ls-tree名字输出八进制转义致中文路径比对全错]]、[[踩坑-gitattributes晚于首次add致备份CRLF被规范化]]、[[踩坑-提交前审查两坑-全暂存区混入空文件与课程样例误判]]
- 相关分类：`03-通用/03-调试与验证`、`03-通用/04-工程规范与安全`
- 相关文档：`E:\fullstack-code\progress.md`（"2026-10-12 零填充事件与处置"、"2026-10-13 Git 仓库重建"两节）
