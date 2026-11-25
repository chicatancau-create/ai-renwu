---
title: 公开仓历史 PII 清洗用 git-filter-repo 镜像克隆法（不伤工作仓 WIP）
category: 03-通用/03-调试与验证
status: verified
date: 2026-11-25
tags: [git, filter-repo, 历史重写, 脱敏, 双远端, force-push]
---

# 一句话结论

公开仓要把历史里的手机号/邮箱等 PII 彻底清掉，用「镜像克隆 → git-filter-repo --replace-text → force-push --mirror 两端 → 工作仓同步」四步，全程不碰工作仓的未提交改动；先 mirror 备份可回滚。

# 触发

仓库已转公开，但 secretscan 发现历史提交里仍有真实手机号/第三方邮箱（当前文件已脱敏，历史可查）。要把公开历史也清干净。

# 复现步骤（已验证）

1. **装工具**：bundled python `C:\Users\Admin\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe -m pip install git-filter-repo --proxy http://127.0.0.1:7890`。Scripts 目录不在 PATH，调用用 `python -m git_filter_repo`（不是 `git filter-repo`）。
2. **备份**：`git clone --mirror <工作仓> G:\数据备份\历史清洗备份_<date>\<name>-pre.git`（含全部 refs/objects，可回滚）。
3. **干净工作镜像**：`git -c http.proxy=http://127.0.0.1:7890 clone --mirror <GitHub远端URL> <name>-work.git`。**从远端克隆而非工作仓**——工作仓带 `refs/remotes/*` 陈旧跟踪引用，mirror 克隆会继承，force-push --mirror 时把它们一起推上去引发 `cannot lock ref ... is at X but expected Y`。远端只有 refs/heads/tags，干净。
4. **替换文件**（UTF-8 无 BOM，字面量 `旧==>新`）：
   ```
   15116765432==>13800138000
   zs@163.com==>demo@example.com
   ```
5. **重写**：在 work.git 内 `python -m git_filter_repo --replace-text <file> --force`。验 `git grep -I -l '<PII>' $(git rev-list --all)` 命中 0。
6. **强推两端**：`git -C work.git -c http.proxy=http://127.0.0.1:7890 -c http.postBuffer=524288000 push --force --mirror <GitHubURL>`（重试 4~5 次，GitHub 直连不稳）；GitCode 直连 `push --force --mirror <GitCodeURL>`。
7. **同步工作仓**（关键，防守护推回旧历史）：
   - 干净仓（如 D:\Skills）：`git fetch origin`（代理）→ `git reset --hard origin/main`。
   - 有 WIP 仓（如 E:\fullstack-code）：`git fetch origin` → `git reset --soft origin/main`，**只移分支指针，index/工作树不动，未提交改动逐条保留**（验 status --porcelain 前后一致）。

# 根因 / 关键坑

- **wire_guard 竞态**：`D:\Skills\skill-router\wire_guard.py --watch`（常驻 pythonw）会在技能文件变动后调 `git_backup.py` 自动 commit+push。历史重写 force-push 时它可能把旧 HEAD 推上远端，造成 `remote rejected cannot lock ref`。对策：重写后立刻把工作仓 reset 到重写 HEAD，使本地=远端，守护再推也是干净历史。
- **mirror 克隆工作仓的 refs/remotes 污染**：见步骤 3，务必从远端克隆工作镜像。
- **filter-repo 会移除 origin 远端**：本流程在独立 work.git 里跑，工作仓远端不受影响；推完用 URL 直推，无需重设远端。
- **本地旧对象残留**：reset 后工作仓对象库仍含旧 PII（不可达），仅本机可见、不会推送；要彻底可 `git reflog expire --expire=now --all && git gc --prune=now --aggressive`（可选）。

# 验证

本轮 fullstack-code（217 提交）手机号/邮箱 17 处→0，HEAD daf076a→500d573；ai-skills（67 提交）第三方邮箱→0，HEAD caae70e→0ec3aa3。两端 force-push 后 ls-remote HEAD 一致；工作仓 WIP 14 条改动前后逐条相同。

# 适用 / 剩余风险

- 适用：个人备份仓、无协作者克隆的公开仓历史脱敏。force-push 改全部 SHA，有他人克隆/fork 时会分叉，需先评估。
- 剩余风险：device flow 授权（gh auth refresh -s delete_repo）直连可能 HTTP 503，挂 HTTPS_PROXY=7890 重试；delete_repo 必须浏览器点授权，非交互拿不到。

# 关联

- 前篇：`规则-两端仓库对齐写操作GitCode增删改UTF8字节body与gh改公开删仓scope.md`
- 脱敏先例：`规则-仓库公开前脱敏须扫全历史且改证据要重签哈希清单.md`