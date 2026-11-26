---
分类: 03-通用/04-工程规范与安全
状态: verified
日期: 2026-11-26
---

# 规则：清理 git 污染时不得删除白名单外的真实未跟踪工作目录

## 一句话结论

ai-renwu（G:\AIrenwu）的 `.gitignore` 首行 `/*` 白名单只放行 `脚本库/02_项目代码/本地AI使用手册`，因此**大量真实工作目录（其它任务产出、根 AGENTS.md、.agent-teams 等）长期处于未跟踪态**。清理"git 历史污染"时，若用「磁盘顶层 minus 跟踪树」判定污染，会把这些真实未跟踪目录误当污染删除。

## 正确判定

- 污染 = 被**错误历史 TRACKED** 的外来文件：用 `git diff --name-only <远端正确SHA>..<本地污染SHA>` 的 **additions** 判定（如 ppt-master/global-memory/skill-router 等 ai-skills 内容）。
- 未跟踪（untracked/ignored）目录**一律不动**；它们不是污染。
- 修复污染分支用 `git reset --mixed <远端SHA>`（保工作树），再外科式提交需要的文件；**不要** `reset --hard` 覆盖未提交真实改动。
- 任何删除前先备份或确认有副本；junction 先查 `LinkType` 防删穿目标。

## 本轮事故（教训）

2026-11-26 清理 ai-renwu 本地 ai-skills 污染时，误用「磁盘 minus 跟踪树」删除 59 项，其中混入真实未跟踪目录：`10_视频广告`、`鸿蒙歌单数据`、`OpenRevo插件整理`、`disk_reports`、`.agent-teams`、`01_浠诲姟掓。`(乱码副本) 等，无副本可恢复；根 `AGENTS.md` 已按原文重建。ai-skills 污染副本（ppt-master 等 489MB）删除正确。

## 关联

- `规则-公开仓历史PII清洗用filter-repo镜像克隆法.md`
- 全局记忆 `D:\Skills\global-memory\feedback-cleanup-git-pollution-not-untracked-workdirs.md`