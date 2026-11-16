---
title: "Gitee 仓库 401 分不清「缺凭据」还是「缺权限」，且用 credential fill 探测会把密钥回显进日志"
date: 2026-11-02
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [git, Git Credential Manager, Gitee, Windows]
tags: [git凭据, GCM, 归因, 探测副作用]
---

# 问题：Gitee 拉取报「用户名或密码错误」，被当成密码问题；顺手用 `git credential fill` 探测又弹出一个会回显密钥的窗口

> 本条把既有记录「Gitee 对不存在回 401，判不了存在」推进为**可判**：给出免凭据的两步判据。

## 一句话结论

Gitee 对「仓库私有/不存在」和「凭据错」回的是**同一句** `Incorrect username or password (access token)`，所以这句话不能当归因依据；判死活改用**属主公开仓库列表 + 匿名 `git ls-remote`**，两步都不需要凭据。另外，**永远不要用 `git credential fill` 探测凭据在不在**——缺凭据时它会弹 GUI 等用户输入，并把输入原样写到 stdout，等于把密钥抄进日志。

## 触发条件与影响

- 项目或功能：按课件地址 `git clone https://gitee.com/<他人>/<仓库>.git` 拉基线工程
- 环境与版本：Windows 11 28000；git 2.52.0.windows.1；GCM 为全局 `credential.helper`，`credential.https://gitee.com.provider=generic`
- 触发条件：目标仓库不在属主的公开列表里（私有或已删）
- 影响范围：归因方向错掉一整轮（去折腾密码/令牌），以及一次密钥落盘风险

## 复现步骤

1. 前置条件：本机对 `gitee.com` 无有效凭据
2. 操作或命令：
   ```bash
   git ls-remote https://gitee.com/lzy_syx/mymall.git
   ```
3. 预期结果：要么列出 refs，要么明确说「无权限/不存在」
4. 实际结果：
   ```
   remote: [session-9a45499a] <本机账号>: Incorrect username or password (access token)
   fatal: Authentication failed for 'https://gitee.com/lzy_syx/mymall.git/'
   ```
   补一次正确格式的凭据后**仍然是同一句**——因为问题根本不在凭据。

## 证据

免凭据两步判据（本轮实测）：

```
https://gitee.com/lzy_syx/projects  -> 200，公开仓库含 harmonyMall / testStore / node-assignment …，不含 mymall
https://gitee.com/lzy_syx/mymall    -> 403 Forbidden（私有页与反爬页同码，单独不可用）
git ls-remote --heads https://gitee.com/lzy_syx/harmonyMall.git -> 6a52f73  refs/heads/master   （匿名直取成功）
git ls-remote --heads https://gitee.com/lzy_syx/testStore.git   -> master + other              （匿名直取成功）
```

同域同属主的另两个仓库匿名可取 ⇒ 网络、代理、GCM 全部排除；`mymall` 拿不到是**可见性**问题。

凭据侧状态（只读探测）：

```
cmdkey /list 里 git:https://gitee.com 条目：认证失败后为 NO（GCM 认证不过不落盘）
```

**判「这个 gitee 账号到底存不存在」要用对照测试**（同轮补测）：

```
https://gitee.com/zhoumoyukuai            -> 200，title「Privacy (zhoumoyukuai) - Gitee.com」，/projects 仓库列表为空
https://gitee.com/lzy_syx                 -> 200，title 是真名，/projects 有 harmonyMall / testStore …
https://gitee.com/this_should_not_exist_zzz9 -> 404（对照组）
```

⇒ 账号存在性看**状态码**（200 vs 404）可靠；但 `title` 出现 `Privacy(<user>)` 且仓库列表为空，是**该用户开了主页隐私**，
不代表账号不存在，也不代表他没仓库 —— 所以「列表里没有目标仓库」这一判据**只对公开列表非空的属主成立**。

## 根因分析

- 已确认的根因一（归因层）：Gitee 把「未授权」统一渲染成「用户名或密码错误」，401 文案不含权限信息；私有仓库的网页端又回 403，与反爬同码。单看任何一层状态码都判不了。
- 已确认的根因二（工具层，本次自己引入）：`git credential fill` / `git-credential-manager get` 在**没有存凭据**时会弹图形窗口向用户要凭据，并把返回的 `username=` / `password=` 明文写进 stdout。我最初拿它做「凭据还在不在」的探测，触发了一个用户可见的弹窗，且用户输入会进本会话的输出文件。
- 排除过的假设：GCM 未安装/未配（`credential.helper` 已指向 `git-credential-manager.exe`）；网络或代理问题（同属主其他仓库匿名 200）；用户名格式写错（换凭据后同一句）。
- 问题归属：环境或依赖（Gitee 的报错设计）+ 本次修改引入（探测方式选错）。

## 最小修复

1. **判仓库死活**：先 `GET https://gitee.com/<属主>/projects` 看目标名在不在公开列表；再 `GIT_TERMINAL_PROMPT=0 git ls-remote <url>` 试匿名直取。两者交叉才下结论；命中不了就去找仓库主人加成员，或核对地址是否写错（本例课件地址 `mymall` 与真实存在的 `harmonyMall` 只差几个字母）。
2. **判凭据在不在**：只读 `cmdkey /list`（注意目标名是 `LegacyGeneric:target=git:https://<host>`，不带 `https://` 会假阴性）。**不要**用 `credential fill`。
3. **要弹窗让用户重填**：走真实 git 命令触发，`GIT_TERMINAL_PROMPT=0` 时不会弹；GCM 的 generic 窗口只把凭据交给 git 与 Windows 凭据管理器，不进 stdout。
4. 认证失败后 GCM 不存凭据，无需手工清理；若存了坏凭据用 `printf 'protocol=https\nhost=<host>\n\n' | git credential reject` 或 `cmdkey /delete:git:https://<host>`。

## 验证记录

- [x] 免凭据判据实跑：属主公开列表无 `mymall`；同属主 `harmonyMall`/`testStore` 匿名 `ls-remote` 成功
- [x] 凭据状态只读复核：`cmdkey /list` 前后对比（有→无），未使用 `fill`
- [x] 弹窗通路验证：GCM 窗口出现（`EnumWindows` 按 PID 命中「Git Credential Manager」），用户输入后由 git 消费
- [x] 误弹窗口已终止，未留下半份凭据
- [ ] 用户当时输入的密码本身对不对：**未证实**（被拒后不落盘，无法复核）

## 可复用规则

- 看到 `Incorrect username or password` 且仓库在**别人名下**：先做免凭据可见性判定，再谈凭据。
- 探测类命令先问一句「它会不会向用户要输入、会不会把结果打到 stdout」；会的话换只读接口。
- 报错文案里的归属信息（本例是 `remote: <账号>:`）要留着，它证明服务器认出了账号——但认出不等于授权。

### 2026-11-02 同日补证：`git push --dry-run` **不是无副作用的探测**

为验证「双 pushurl 恢复后两端是否都应答」跑了一次 `git push --dry-run origin main`。它确实不写远端，
但**会真走一次认证**：第一个 pushurl（gitcode）用存的那条凭据认证被拒后，git 照常调用 `credential reject`，
把 Windows 凭据管理器里的 `git:https://gitcode.com` **删掉了**。事后 `cmdkey /list` 只剩 `gh:github.com:*` 两条。

⇒ 三条规则：
1. **`--dry-run` 只保证不写 ref，不保证不碰凭据**；想验通路优先用 `git ls-remote`（纯 fetch，不触发 reject）。
2. 多 `pushurl` 时 **git 撞第一个失败就中止**，后面的 URL 根本轮不到 ⇒ 「一次落两端」的结构决定了
   **一端凭据坏 = 两端都推不上**，别以为另一端还能侥幸收到。
3. 删掉的凭据只能让用户重填，AI 无法恢复；给用户派活前先想清楚这次探测会不会吃掉他的凭据。

同轮另一条正向验证：`git push --dry-run <单个 GitHub URL>` 回 `* [new branch] main -> dualpush-check`，
证明 GitHub 侧认证通路完好——**用显式单个 URL 探**，就不会连累另一端的凭据。

**由此得到一条可复用的正向技巧：怎样「只为弹认证窗并落凭据」而不发布任何东西。**

```bash
git push --dry-run https://<host>/<owner>/<repo>.git main:refs/heads/cred-check
```

`--dry-run` 让服务端协商照常发生但**不创建 ref**，而认证是真实走的 ⇒ GCM 弹窗、用户填令牌、
凭据落进 Windows 凭据管理器，远端却什么都没多出来。事后两条收尾断言必跑：
`cmdkey /list` 里 `git:https://<host>` 回来了；`git ls-remote --heads <url>` 里**没有** `cred-check`。
（对比：直接对多 pushurl 的 remote 跑 `--dry-run` 会先撞第一个失败并删凭据，所以**必须用显式单 URL**。）

### 「凭据到底通没通」的完整证据链（同轮，被用户追问后补做）

先承认一个假证据：**公开仓库匿名 `ls-remote` 也能拿到 refs**，所以「读得到」证明不了任何凭据。
要证「写凭据可用」得凑齐四步，缺一步都下不了结论：

```
① 对照：GET /info/refs?service=git-upload-pack   -> 200   （匿名可读，故读操作不能当证据）
② 对照：GET /info/refs?service=git-receive-pack  -> 401   （匿名写协商被拒 = 该端点真的校验）
③ 对照：带明显错的凭据打 receive-pack            -> 401   （不是"给什么都放行"）
④ 实验：GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never git push --dry-run <单URL> main:refs/heads/x
        -> * [new branch] 且 rc=0                （禁弹窗 ⇒ 用的只能是"已存进凭据管理器"的那条，
                                                   不是弹窗当场输入的那份内存凭据）
⑤ 收尾：git ls-remote --heads <URL> 里没有那个临时 ref 名（证明确实没发布）
```

`--dry-run` 会打印 `* [new branch]` 是因为它拿到了服务端**授权后**的 receive-pack ref  advertisement；
凭据无效时同一命令直接 `fatal: Authentication failed`（本轮修凭据前就是这句），两者可分辨。
另记一条环境噪声：`gitcode.com` 当时解析要 **11.4 s** 并偶发 `Could not resolve host`，
一次 A/B 因此整组作废 —— **网络层失败会把认证实验一起污染**，先用 `--resolve <域名>:443:<IP>` 绕开 DNS 再测。

## 适用范围与不适用范围

- 适用：Gitee、GitCode/AtomGit 等「401 文案不区分权限」的托管站；任何配了 GCM generic provider 的 HTTPS 仓库
- 不适用：GitHub（GCM 走 OAuth，未授权与无权限文案可区分）；SSH 协议仓库（权限报错是 `Permission denied (publickey)`）
- **跨平台不通用**：`gitee.com/<属主>/<仓库>` 与 `atomgit.com`（= `gitcode.com`）是**两套独立账号体系**，
  课件给的域名决定该登哪个站。本轮实测同一 `lzy_syx/mymall` 在 atomgit/gitcode 域名下回
  `<CH.00905403> The project you were looking for could not be found` + 403，即该仓库只存在于 gitee，
  拿 AtomGit 的账号密码去填 gitee 弹窗必然失败。

## 剩余风险

- Gitee 网页 403 与反爬同码，若属主公开列表被折叠/分页，「不在列表里」可能误判为私有；本例列表页 200 且含多个仓库，判据成立，但换站点需重新验。
- 属主把主页设为 `Privacy(<user>)` 时 `/projects` 会**整列空**，此时「不在列表里」判据失效（见上节对照测试），只能退回「问仓库主人 / 让用户在已登录浏览器里打开该仓库页」两招。
- 用户真实密码是否输错未证实，不能排除「凭据也错」叠加「仓库也没权限」两种问题同时存在。

## 关联

- 相关记录：[[规则-AtomGit与GitHub差异与国内推送判据]]（同属「状态码不能单独判存在性」）、[[踩坑-AI面板连接失败耗时1ms是没填密钥而非网络]]（同类：报错文案把归因带偏）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关命令：`git ls-remote`、`cmdkey /list`、`git credential reject`
