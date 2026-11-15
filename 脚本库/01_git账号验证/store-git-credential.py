#!/usr/bin/env python
"""把 GitCode / AtomGit 的 HTTPS 推送凭据存进 Windows 凭据管理器。

令牌不回显、不进命令历史、不落任何文件日志。
入口：右上角头像 → 个人设置 → 左侧「访问令牌 / API 密钥」→ 新建。

  python store-git-credential.py --prompt                  # 交互式隐藏输入(推荐)
  python store-git-credential.py --prompt --host atomgit.com
  python store-git-credential.py <凭据文件路径>              # 从文件读 username=/token=

两个已实测的坑，用之前必须知道：

1. **用户名要填平台 handle（@ 后面那个），不是 git 的 `user.name`。** 填错的话 GitCode 回的是
   `HTTP Basic: Access denied` + 「密码认证已停用，请用令牌」这种误导性文案，看着像令牌过期。
2. **凭据按 `host + username` 建条目**（Windows 凭据管理器里的 target 是
   `git:https://<用户名>@<域名>`）。所以换过一次用户名后，旧条目还在、会被优先命中，
   光重写同一条不会生效。清掉它：

       cmdkey /delete:git:https://<旧用户名>@gitcode.com

   注意查询也要带 `https://`：`cmdkey /list:git:https://gitcode.com`，少写会假报「无」。
   另外认证**失败一次** git 就会 `credential reject` 把条目删掉，列表查不到 ≠ 你没存过。
"""
import getpass
import os
import re
import subprocess
import sys

DEFAULT_HOST = "gitcode.com"
# GitCode/AtomGit 的访问令牌形如 <2 位前缀>-<约 22 位字母数字>，这里只按字符集与长度校验
TOKEN_SHAPE = re.compile(r"^[A-Za-z0-9_\-]{16,64}$")


def check_token_shape(token):
    """拦住误粘贴: 命令串、URL、带空格或反斜杠的东西都不是令牌。"""
    if not TOKEN_SHAPE.match(token):
        sys.exit(
            "这不像访问令牌(应为 16-64 位字母数字, 可含 - 和 _, 不能有空格/反斜杠/引号)。\n"
            "只粘贴令牌本身, 不要把调用命令粘进来。已中止, 未写入。"
        )


def store(host, username, token):
    payload = "protocol=https\nhost=%s\nusername=%s\npassword=%s\n\n" % (host, username, token)
    result = subprocess.run(
        ["git", "credential", "approve"],
        input=payload,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        # git 的报错正文可能带 URL 或用户名, 只报退出码
        sys.exit("git credential approve 失败, 退出码 %d" % result.returncode)
    print("已提交给凭据助手: host=%s username=%s 密钥尾号 ****%s" % (host, username, token[-6:]))
    print("核对条目(不显示密钥本身): cmdkey /list:git:https://%s" % host)
    print("下一步验证令牌是否真能用: python verify_gitcode.py  或  git ls-remote <你的仓库>")


def from_prompt(host):
    print("目标域名 %s" % host)
    print("提示: 用户名填平台 handle（@ 后面那个），**不要**直接回车用系统账户名 ——")
    print("      Windows 的 %USER% 是本地账户名, 拿它当平台用户名就会认证失败, 而且报错像令牌过期。")
    try:
        username = input("GitCode/AtomGit 用户名: ").strip()
        token = getpass.getpass("访问密钥(输入不回显): ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\n已取消, 未写入任何凭据")
    if not username:
        sys.exit("用户名为空, 已中止（留空会落到系统账户名, 正是最常见的错法）")
    if not token:
        sys.exit("密钥为空, 已中止")
    check_token_shape(token)
    store(host, username, token)


def from_file(path, host):
    if not os.path.isfile(path):
        sys.exit("凭据文件不存在: %s" % path)
    fields = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                fields[key.strip().lower()] = value.strip()
    username = fields.get("username")
    token = fields.get("token") or fields.get("password")
    if not username or not token:
        sys.exit("凭据文件需要 username= 和 token= 两行且都不能为空")
    check_token_shape(token)
    store(host, username, token)


def main():
    args = sys.argv[1:]
    host = DEFAULT_HOST
    if "--host" in args:
        i = args.index("--host")
        if i + 1 >= len(args):
            sys.exit("--host 后面要跟域名")
        host = args.pop(i + 1)
        args.pop(i)
    if "--prompt" in args:
        from_prompt(host)
    elif args:
        from_file(args[0], host)
    else:
        # 不再默认去找某个凭据文件: 那个路径已随会话归档失效, 静默指向不存在的文件只会误导
        sys.exit("用法: store-git-credential.py --prompt [ --host <域名> ]  或  指定凭据文件路径")


if __name__ == "__main__":
    main()
