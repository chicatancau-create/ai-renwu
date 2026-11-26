---
分类: 03-通用/03-调试与验证
状态: verified
日期: 2026-11-26
关联: 规则-两端仓库对齐写操作GitCode增删改UTF8字节body与gh改公开删仓scope.md
---

# 规则：公开仓历史 PII 清洗用 filter-repo 镜像克隆法

> 2026-11-26 补建：本文件此前被 SKILL.md 症状索引引用但实体缺失（断链），按本轮 ai-skills / fullstack-code 两次清洗的实测经验重建。不含任何真实凭据/邮箱/手机号，示例一律占位符。

## 一句话结论

公开仓要把**历史里**的第三方 PII（邮箱/手机号/用户名/显示名）清掉，唯一可靠做法是：从**远端** `clone --mirror` 出干净镜像 → `git-filter-repo --replace-text` 重写 → `push --force --mirror` 两端 → 工作仓 `fetch + reset` 同步 → `reflog expire + gc --prune=now` 清本地不可达对象。**不要**在已坏的历史上二次 replace，**不要**从工作仓直接 mirror（会继承 `refs/remotes` 污染）。

## 适用 / 不适用

- 适用：仓库已公开或即将公开，历史 blob 含第三方 PII，需要 ref 层零残留。
- 不适用：仅当前文件含 PII 而历史干净（直接脱敏当前文件+外科式 commit 即可）；含真实密钥/Token 的泄露（那属安全事件，需轮换凭据，不只是 rewrite）。

## 四步法（命令骨架）

1. **备份**：`git clone --mirror <远端> <备份>.git`（pristine，保留原始历史供回滚/重做）。
2. **干净镜像**：`git clone --mirror <远端URL> work.git`（从远端克隆，refs 干净；勿从工作仓 mirror）。
3. **重写**：在 work.git 目录内原地跑
   `python -m git_filter_repo --force --replace-text replace.txt`
   （`git filter-repo` 命令不在 PATH 时用 `python -m git_filter_repo`；**不能加 `--source`**，会静默回滚、refs/对象不落盘）。
   replace.txt 每行 `旧串==>新串`，**必须同时含裸用户名与完整邮箱，且长串在前**（先替完整邮箱再替裸用户名，避免短串先命中破坏长串）。
4. **强推+同步+清本地**：
   `git push --force --mirror <GitHub>`（挂代理 `-c http.proxy=http://127.0.0.1:7890`）与 `<GitCode>`（直连）；
   工作仓 `git fetch <remote> --prune` + 干净仓 `reset --hard`／有 WIP 仓 `reset --soft`（保 index/工作树）；
   `git reflog expire --expire=now --expire-unreachable=now --all` + `git gc --prune=now`。

## 六个坑（本轮实测）

1. replace 文件只写完整邮箱→裸用户名漏替；且目标串若被按 GBK 写坏会产生乱码占位符。replace.txt 必须 UTF-8 无 BOM、含裸串、长串在前。
2. 验漏用 `git log --all -S <串>`（pickaxe）或逐提交 `git grep <rev>`，**不要**只用 `log --all -p | grep`（上一轮漏检正因后者）。
3. 必须从 pristine 备份重做，不要在坏历史上二次 replace。
4. filter-repo 加 `--source` 会打印新 SHA 但静默回滚；改为镜像目录内原地 `--force`。
5. rewrite 后本地残留不可达旧 PII 对象，必须 `reflog expire + gc --prune=now` 才清零。
6. 本地远端跟踪引用（如 `atomgit/main`）可能 stale 停在 pre-purge SHA，造成"假残留"；先 `fetch --prune` 再验。

## 平台对象层残留（git 做不到，需工单）

force-push 只清 **ref 层**；GitHub/GitCode 的**对象层**仍可按旧 SHA 用 API 取到旧 blob（`GET /repos/.../git/blobs/<sha>`、`?ref=<旧SHA>`）。正常 clone/fetch/浏览拿不到（ref 层 100% 干净），但知 SHA 者仍可取。要真零残留须向 **GitHub Support 提工单申请强制 GC 不可达对象**；GitCode 无自助入口，只能等平台回收或联系平台方。`forks_count=0` 时无 fork 副本留存。

## 协调自动备份守护

D:\Skills 有 `skill-router/wire_guard.py --watch`（pythonw）会在技能文件变动时自动 commit+push，与 force-push 竞态。重写期间 `Stop-Process` 停掉，收尾再 `Start-Process pythonw wire_guard.py --watch` 重启；重启后它推的是新历史，不会推回旧对象。

## 验证口径（多重）

- `log --all -p` 逐串 0 命中；pickaxe `-S` 0 提交；逐提交 `git grep` 0；
- 从两端**全新克隆**重跑全部检查 0；
- 对象级 `git cat-file --batch-all-objects --batch` 扫不可达对象 0；
- 旧尖端 SHA 在本地与远端 clone `Not a valid object name`；
- `fsck --connectivity-only` 无 error；本人标识符保留计数不变。

## 关联

- 写操作通路见 `规则-两端仓库对齐写操作GitCode增删改UTF8字节body与gh改公开删仓scope.md`。
- 全局记忆 `D:\Skills\global-memory\reference-public-repo-history-pii-purge.md`（含本轮 6 教训）。