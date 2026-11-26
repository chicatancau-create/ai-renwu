---
title: "踩坑-DSH 清空归档时归档会话跳出归档状态并留幽灵行"
date: 2026-11-19
domain: backend
category: 插件与集成
status: needs-review
severity: medium
stack: [DeepSeek Harness, Cordis 插件, @local/archived-cleanup]
tags: [归档, 侧栏, 幽灵行, unarchive, api-session/removed]
---

# 问题：点「清空归档」后会话从归档状态跳出、删除后侧栏仍留打不开的行

## 一句话结论

旧实现的删除顺序是「先 `unarchiveSession` 再删文件」：unarchive 立刻推送到前端让行退回可见状态，而删文件没有任何前端通知，于是既“跳出归档”又留下幽灵行；另外归档本身不解除工作区归属，所以归档行不会进「未分组」。

## 触发条件与影响

- 项目或功能：DSH 桌面版侧栏的归档 + 自研插件 `@local/archived-cleanup`（底部「清空归档」、右键「删除会话」）。
- 环境与版本：DSH 桌面版（asar 安装，`DSH_PROFILE=desktop`），插件 `@local/archived-cleanup` 1.0.0。
- 触发条件：右键会话「归档会话」→ 行变灰；再点底部「清空归档」。
- 影响范围：归档行位置错（留在原分组而不是「未分组」）；删除后行残留；数据目录与投影缓存可能只删一半。

## 复现步骤

1. 前置条件：`storages/workspace.json` 的 `global.archivedSessionIds` 含目标会话。
2. 操作或命令：客户端调用 `remote.archivedCleanup.deleteSession(id)`（旧实现）。
3. 预期结果：行消失，磁盘目录与 `storages/session_projcache/sessions/<uuid>.json` 一起删除。
4. 实际结果：行先退回普通状态（灰底消失），文件删除无通知，行留到重启。

## 证据

- 旧 `index.js` 顺序：`await registry.unarchiveSession(sessionId)` → `rm(sessions/<slug>/<id>)` → projcache 删除。
- 前端行的增删只认两个来源：`api-session/added|removed` 事件，或 `sessions.refresh()` 重新拉取（`dsh-api-session-controller/src/client/sessions/manager.ts` 的 `handleSessionRemoved` / `refreshList`）。
- `dsh-session-query/src/corpus.ts` 的 `listSessions` 会把**内存里所有 live session** 合并进列表，所以“删了文件但没通知”的行会一直被拉到。
- `dsh-workspace/src/index.ts` 注释原文："Archiving never touches workspace accounting — an archived session keeps its `sessionIds` slot"，所以归档行不会自动进「未分组」。

## 根因分析

- 已确认的根因：3 个独立缺陷叠加 —— (a) 删除前先 unarchive；(b) 删文件后不发 `api-session/removed`；(c) 归档不解除工作区归属。
- 排除过的假设：不是前端缓存 bug；不是 better-sidebar 干扰（其 archive 只用于 side chat）。
- 问题归属：修改前已有。

## 最小修复

插件 `G:\AIrenwu\03_备份\archived-cleanup-20261115\`（index.js / client.js）：

1. 监听 `workspace/session-archived`，在 `setTimeout(0)` 里把会话从所有工作区 `detachSession`（归档 → 落「未分组」）。
2. `deleteSession` 改成：detach → 删目录 + 删 projcache（含 `session-` 前缀与裸 uuid 两种文件名）→ `ctx.emit('api-session/removed', id)` → 仅在**非热**会话时 unarchive。
3. 启动 5s 后 `sweepArchived()`：归档集合里既不在磁盘也不在内存的 id 自动 unarchive（清历史幽灵）。
4. 客户端：删掉 `sidebar.workspaces.session.menu.item` 的「删除会话」；「清空归档」保留二次确认，删除后调用 `ctx.get('sessions').refresh()`。

## 验证记录

- [ ] 格式化或静态检查：`--check` 通过
- [ ] 类型检查或编译：不适用
- [ ] 单元、集成或端到端测试：假 ctx + 临时 DSH home 冒烟：归档事件触发 detach；`deleteAllArchived` 返回 `{deleted:[id],failed:[],warm:[]}`；目录与 projcache 均被清除
- [ ] 构建：不适用
- [ ] 启动或手动回归：**待用户回归**（归档是否落「未分组」、清空归档是否无幽灵行）

## 可复用规则

- 删除“宿主也在内存里持有”的资源时，顺序必须是「先删持久化 → 再广播移除事件 → 最后才动可见性状态」，且移除事件要显式发（`api-session/removed`），不要指望文件系统变化能传播到前端。
- 对热会话（进程内还活着）不要 unarchive：保持归档态才能让行继续被过滤器藏住，否则会立刻变成可见幽灵。

## 适用范围与不适用范围

- 适用：DSH 插件里做“删除/回收 session”类操作；任何“宿主内存 + 磁盘 + 前端列表”三处状态需要同步的删除流程。
- 不适用：仅逻辑归档、不删数据的场景。

## 剩余风险

- 热会话无法被插件驱逐（`AgentRegistry`/`SessionStore` 没有公开的 dispose-by-id），其内存条目要等下次启动才消失；表现为“已删除但过滤器显示归档时仍能看到一条不可打开的行”。
- 归档后 detach 会让「取消归档」把会话还回「未分组」，而不是原分组。

## 关联

- 相关记录：无
- 相关分类：02-后端
- 相关代码、命令或文档：`dsh-workspace/src/index.ts`（archiveSession/unarchiveSession）、`dsh-api-session-controller/src/index.ts:224-229`、`dsh-session-query/src/corpus.ts:62-87`
