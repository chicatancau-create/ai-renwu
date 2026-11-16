---
title: ".gitattributes 晚于首次 git add，备份里的 CRLF 被静默规范化；验收必须克隆回来比 sha256"
date: 2026-11-15
domain: common
category: 03-通用/04-工程规范与安全
status: verified
severity: high
stack: [git, Windows, PowerShell, Python]
tags: [备份, gitattributes, CRLF, renormalize, 验收判据, 只读pack]
---

# 踩坑：push 返回 0 不等于备份可用——79 个文件的字节被 git 悄悄改了

## 一句话结论

`D:\Skills` 的第一次 `git add -A` 发生在 `.gitattributes`（`* -text`）写好**之前**，
Windows 上 `core.autocrlf` 默认生效，**79 个文件被 CRLF→LF 规范化后入库**；
补属性后 `git rm -r --cached .` **并没有真正清空索引**，旧 blob 还在。
修法是 `git add --renormalize .`。
**备份的验收标准是「从远端克隆回来逐文件 sha256 一致」，不是「push 返回 0」。**

## 触发条件与影响

- 环境：git 2.55.0.windows.5，Windows，混合编码的技能库（有 BOM、有 CRLF、有 LF）。
- 触发：先 `git init` + `git add -A`，之后才想起写 `.gitattributes`。
- 影响：远端 289 个文件里 **79 个与本地字节不一致**。文本内容看着一样，
  但脚本/BOM/行尾敏感的文件恢复后可能行为不同；「备份成功」是假的。

## 证据

从 4 个远端各做浅克隆，逐文件 sha256 与本地比对：

| 库 | 首轮结果 |
|---|---|
| qoder-toolkit | GitHub 13025/13025 一致、GitCode 13025/13025 一致 ✅ |
| **ai-skills** | **两个远端都是 210 一致 / 79 不一致** ❌ |

- `brave-web-search/SKILL.md`：磁盘 **322 个 CRLF、0 个纯 LF**，
  入库 blob 的 sha ≠ `git hash-object --no-filters <file>`。
- `git check-attr text -- <file>` → `text: unset`（属性已生效），`core.autocrlf=false`（全局），
  但**索引里存的是属性生效之前的旧 blob**。
- **当时的征兆已经出现过**：`git rm -r --cached .` 之后仍有 3 个 WorkBuddy 迁移 JSON staged，
  我只手动 `git rm --cached` 了那 3 个，**没意识到其余 79 个旧 blob 也还在**。
- QoderToolkit 从一开始就没这个问题——它的 `.gitattributes` 在首次 `add` 之前就位。

## 根因分析

- 已确认根因：git 的行尾规范化在 `add` 时按**当时**的属性决定；后补属性不会自动重写已入库的 blob。
- 排除过的假设：远端平台改写内容（两个平台症状完全一致，且 qoder-toolkit 全绿）；
  克隆过程转换（`* -text` 下 checkout 也不转换）。
- 问题归属：**本次修改引入**（我的建仓顺序错了）。

## 最小修复

```
git add --renormalize .          # 按当前属性重新入库
git diff --cached --name-only    # 79 个文件重 staged
# 逐个核对：git hash-object --no-filters <file>  ==  git ls-files -s <file> 的 sha
git commit -m "修正备份字节一致性"
git push origin main && git push gitcode main
```

实测 `mismatches after renormalise: 0`，提交 `16495cb`。

**复验（4 个远端重新浅克隆）**：

```
ai-skills      github   clone 3.8s | identical=289    diff=0 missing=0 | excluded-leaked=none
ai-skills      gitcode  clone 3.0s | identical=289    diff=0 missing=0 | excluded-leaked=none
qoder-toolkit  github   clone 20.3s| identical=13025  diff=0 missing=0 | excluded-leaked=none
qoder-toolkit  gitcode  clone 18.9s| identical=13025  diff=0 missing=0 | excluded-leaked=none
VERDICT: ALL REMOTES RESTORE BYTE-IDENTICAL
```

验收脚本：`G:\AIrenwu\脚本库\06_建仓与双推\verify_restore.py`；
修复脚本：同目录 `fix_byte_fidelity.py`。

## 验证记录

- [x] `git check-attr` 确认属性生效
- [x] 79 个文件重 staged，逐个 `hash-object --no-filters` 与索引 sha 比对 mismatches=0
- [x] 4 个远端浅克隆全量比对：**13314 个文件全部字节一致，0 差异 0 缺失**
- [x] 许可排除的 7 个目录在克隆里一个都没有（`excluded-leaked=none`）

## 可复用规则

1. **`.gitattributes` 必须在第一次 `git add` 之前就位。** 混合编码/含 BOM 的库用 `* -text`
   禁止一切行尾规范化（备份要字节一致）。
2. **`git rm -r --cached .` 不保证清空索引**；要改属性后重新入库，用 **`git add --renormalize .`**，
   并逐个用 `git hash-object --no-filters` 与 `git ls-files -s` 的 sha 核对。
3. **备份验收 = 从远端克隆回来逐文件 sha256 一致**，不是 push 退出码 0，也不是 `ls-remote` SHA 相等
   （后者只证明提交推上去了，不证明内容字节对）。
4. **git 在 Windows 把 pack 文件设成只读**，`shutil.rmtree(..., ignore_errors=True)` 会**静默留下残目录**，
   下一轮 clone 报 `fatal: destination path ... already exists and is not an empty directory`。
   清理临时克隆必须用 `onerror` 里 `os.chmod(path, stat.S_IWRITE)` 后重试。
5. 自动备份守护要**去抖 + 只在真有改动时**提交（本机 10 分钟），推完回读 `ls-remote` 核对 SHA；
   **从不 force-push、不改历史、不删远端分支**。

## 适用范围与不适用范围

- 适用：Windows 上把混合编码目录做 git 备份的任何场景。
- 不适用：纯文本项目且团队约定统一 LF（那时规范化是想要的行为）。

## 剩余风险

- 大库（本机 qoder-toolkit 13025 文件 / 88MB）单次推送约 110–120s，网络抖动会失败；
  已有守护会重试，但**不要在推送中途改库**。
- 浅克隆验收只覆盖 HEAD，不校验历史提交的字节一致性。

## 关联

- [[规则-技能库上传前按许可排除且私有仓库不豁免]]
- [[踩坑-GitHub大包推送被重置需分块推送]]
- [[规则-AtomGit与GitHub差异与国内推送判据]]
- [[踩坑-ls-tree名字输出八进制转义致中文路径比对全错]]（同类「git 输出不能直接当字节证据」）
