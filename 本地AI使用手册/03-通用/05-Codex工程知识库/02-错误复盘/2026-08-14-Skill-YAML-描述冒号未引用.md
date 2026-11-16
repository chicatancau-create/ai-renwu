---
date: 2026-08-14
project: "D:\\Skills"
stack: [Agent-Skills, YAML, Python]
status: verified
tags: [engineering-retrospective, skills, yaml]
---

# 错误：Skill 描述含冒号但未作为 YAML 字符串引用

## 背景、复现与影响

审计 Codex 与 OpenCode 共用的 15 个 Skill。6 个 `SKILL.md` 的 `description` 包含 `: `，但使用未引用的纯量，官方校验器无法解析 frontmatter。

### 复现步骤

1. 前置条件：UTF-8 模式运行 Codex `skill-creator/scripts/quick_validate.py`，并提供 PyYAML。
2. 操作或命令：对含未引用冒号的 Skill 目录运行 `quick_validate.py <skill-directory>`。
3. 预期结果：输出 `Skill is valid!` 并以 0 退出。
4. 实际结果：输出 `Invalid YAML in frontmatter: mapping values are not allowed here`。

## 现象与证据

首次官方校验结果为 `official_validator_passed=9 failed=6`；失败项均在 `description` 中包含未引用的 `: `。

## 问题归属判断

- [x] 修改前已有问题
- [ ] 本次修改引入的问题
- [ ] 环境、依赖或外部服务问题
- 判断依据：正式源的原始 frontmatter 已含这些未引用描述；简化正则检查只核对键名，没有执行 YAML 解析。

## 根因

YAML 的普通纯量不能安全包含 `: `。原有检查没有调用真正的 YAML 解析器，因此把文本结构正确误判为 YAML 有效。

## 最小修复

将全部 15 个 `description` 统一序列化为双引号 YAML 字符串；不改变描述内容或触发语义。

## 验证记录

- [通过] `quick_validate.py` 逐个校验 15 个 Skill — `official_validator_passed=15 failed=0`。
- [通过] Python AST 解析 33 个脚本 — `ast_failed=0`。
- [通过] 32 个 DWS 脚本执行 `--help` — `help_passed=32 failed=0`。
- [未执行] 独立 YAML lint — 官方校验器已实际使用 PyYAML 解析同一 frontmatter。

## 预防规则

创建或批量改写 Agent Skill 时，必须使用真实 YAML 解析器或官方校验器；中文 `description` 一律序列化为带引号字符串。适用于 YAML frontmatter，不要求普通 Markdown 正文加引号。

## 剩余风险

OpenCode 的私有扩展解析器未单独提供，但当前 frontmatter 使用两端共同支持的最小字段，且符合标准 YAML。

## 关联

- 项目：`D:\Skills`
- 相关模式：无
- 相关提交或文件：15 个 `SKILL.md`
