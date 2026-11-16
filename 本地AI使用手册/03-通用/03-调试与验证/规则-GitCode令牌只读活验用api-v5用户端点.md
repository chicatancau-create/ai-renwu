---
title: "GitCode/AtomGit 令牌只读活验：api/v5/user + Bearer，CredReadW 取凭据不回显"
date: 2026-11-12
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: low
stack: [Git, GitCode, AtomGit, Windows, Python]
tags: [凭据, 活验, API, 取证, 安全]
---

# 问题：凭据管理器里「有凭据」不等于「凭据有效」，如何零副作用地活验 GitCode/AtomGit 令牌

## 一句话结论

用 Win32 `CredReadW` 从 Windows 凭据管理器读 `git:https://gitcode.com` / `git:https://atomgit.com`
的令牌（**只留在进程内存，绝不打印**），带 `Authorization: Bearer <token>` 打
`GET https://api.gitcode.com/api/v5/user`（或 `https://gitcode.com/api/v5/user`），
**200 + login 字段 = 令牌有效**。不 push、不 `credential fill`、不弹 GUI、零副作用。
注意 **v4 端点不存在（404）**，别按 GitLab 惯性写 `/api/v4/`。

## 触发条件与影响

- 项目或功能：判断本机存储的 GitCode/AtomGit 令牌是否过期/被吊销。背景：2026-11-02 曾发生
  `git push --dry-run` 认证失败触发 `credential reject` 删掉 gitcode 凭据的事故；重新存上后需要验「真的能用」。
- 环境与版本：Win11 + git 2.55.0.windows.5 + GCM 2.9.1；Python 标准库（ctypes + urllib）即可，无需第三方依赖。
- 影响范围：用错探测法会弹 GUI、回显密钥、甚至再删一次凭据（见 Gitee 记录）。

## 方法与证据（2026-11-12 实测）

1. **先匿名探测，确定端点形状**（不带任何凭据）：
   - `GET https://gitcode.com/api/v4/user` → **404**（NOT_PATH，v4 不存在）；
   - `GET https://api.gitcode.com/api/v5/user` → **401**；
   - `GET https://gitcode.com/api/v5/user` → **403 "no scopes:read_user"**（端点存在，匿名被拒）。
2. **CredReadW 读凭据**（advapi32，目标名 `git:https://gitcode.com` 与 `git:https://atomgit.com`，
   CRED_TYPE_GENERIC）：两条都在，`UserName=zhoujinwei`，CredentialBlob 长度 24 字节；密钥全程未打印。
3. **带 Bearer 打两个 v5 端点** → 均 **200**，响应体
   `{"id":"69034771cea88736a188234c","login":"zhoumoyukuai","name":"zhoumoyukuai"}`
   → 两条令牌都有效，且属同一账号。
4. **命名空间事实**：凭据里的用户名 `zhoujinwei` 是别名命名空间，规范 login 是 `zhoumoyukuai`；
   两个命名空间的仓库 URL 指向同一后端（见 AtomGit 记录）。
5. **同法可查绑定邮箱**（2026-11-12 追加实测）：`GET https://gitcode.com/api/v5/emails` 带 Bearer → **200**
   `[{"email":"chicatancau@gmail.com","state":"confirmed"}]`；`/api/v5/user/emails` 不存在（404）。
   用于核实「账号绑了哪个邮箱」（提交归属判据），同样零副作用；脚本 `G:\AIrenwu\脚本库\01_git账号验证\check_gitcode_emails.py`。

## 为什么不用别的办法

- `git credential fill`：弹 GUI 且把密钥回显进 stdout（见 Gitee 401 记录）。
- `git push --dry-run`：认证失败会 `credential reject` **删掉凭据**，探测本身有破坏性。
- 公开仓库匿名 `ls-remote`：只证明链路通，**证明不了凭据**（匿名就放行）。
- `cmdkey /list`：只证明「存了」，不证明「有效」。

## 验证记录

- [x] 匿名探测、CredReadW 读取、带令牌请求全部于 2026-11-12 实跑（脚本 `G:\AIrenwu\脚本库\01_git账号验证\verify_gitcode.py`）。
- [ ] 令牌到期时间未知：API 不返回过期时间，需要时重跑本方法复验。

## 可复用规则

判 GitCode/AtomGit 凭据有效性 = **CredReadW 读（不回显）+ GET api/v5/user 带 Bearer**：
200+login=有效，401=失效/过期。动手前先匿名打一次确认端点还在（平台会改 API 形状）。
查绑定邮箱用 `GET api/v5/emails`（不是 `/user/emails`，后者 404）；`state=confirmed` 才可作提交归属判据。

## 适用范围与不适用范围

- 适用：GitCode/AtomGit（同一后端）的个人访问令牌；两条凭据分别验或合并验都行。
- 不适用：Gitee（另一家账号体系，v5 形状类似但本轮未实测）；GitHub（用 `gh api user -X GET`）。

## 剩余风险

平台可能改 API 形状或 scope 要求；令牌长度 24 字节是当日事实。本记录不含任何令牌值。

## 关联

- 相关记录：[[踩坑-Gitee仓库401分不清缺凭据还是缺权限且fill探测会回显密钥]]、
  [[03-通用/04-工程规范与安全/规则-AtomGit与GitHub差异与国内推送判据]]
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码：`G:\AIrenwu\脚本库\01_git账号验证\verify_gitcode.py`（ctypes CredReadW + urllib，只打印状态码与身份字段）
