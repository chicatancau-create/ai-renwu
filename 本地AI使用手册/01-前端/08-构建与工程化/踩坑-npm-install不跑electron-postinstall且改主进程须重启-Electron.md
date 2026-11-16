---
title: "npm install 不执行 electron 的 postinstall，桌面端起来没有二进制；改主进程后 HMR 不生效"
date: 2026-11-15
domain: frontend
category: 构建与工程化
status: verified
severity: medium
stack: [Electron, npm, Vite, Windows]
tags: [electron, postinstall, 本地部署, HMR, 主进程]
---

# 问题：装完依赖 electron.exe 是空的，且改 main/preload 后跑的还是旧代码

> `needs-review` 表示尚未完成验证；只有复现、定位、修复和验证都完成后，才改为 `verified`。

## 一句话结论

`npm install` 成功退出（exit 0）**不代表 electron 的二进制下下来了**——它的 postinstall 可能被整跳；判据是看 `node_modules/electron/dist/` 与 `path.txt` 是否存在，而不是看安装退出码。另外 Electron 的**主进程与 preload 改动不会被 Vite HMR 接住**，必须重启整个应用。

## 触发条件与影响

- 项目或功能：任何以 `electron` 为 devDependency、用 Vite/webpack 起渲染层的本地部署任务。
- 环境与版本：Windows 11 + npm 11.x + Node 24，`electron` 43.x（其他大版本行为未测）。
- 触发条件：`npm install --no-audit --no-fund` 后直接 `npm run dev:electron`。
- 影响范围：应用完全不启动（无窗口、无报错，只在 console 里静默）；以及误以为主进程代码已生效而得出错误结论。

## 复现步骤

1. 前置条件：一个含 `dev:electron` 脚本的 Electron 工程，已 `npm install`。
2. 操作或命令：检查 `node_modules/electron/dist/electron.exe` 与 `node_modules/electron/path.txt`。
3. 预期结果：两者都在，`electron` 可执行。
4. 实际结果：`dist/` 不存在、`path.txt` 不存在，但 `npm install` 退出码为 0、日志里只有 deprecation 警告，没有任何失败提示。

## 证据

- 该工程 `npm install` 日志末尾：`added 1170 packages in 1m` + `EXIT=0`，随后 `ls node_modules/electron/dist/electron.exe` → `No such file or directory`，`cat path.txt` → `No such file`。
- 手动补跑后：`node node_modules/electron/install.js` 打出 238,984,704 字节的 `electron.exe`，`path.txt` 内容为 `electron.exe`，应用随即正常启动。

## 根因分析

- 已确认的根因：本机的 npm 版本/配置组合下，electron 包的 postinstall 没有被执行（不报错、不留痕）。次生根因：Vite 的 HMR 只覆盖渲染层模块图，`electron/main.*`、`preload.*` 属于主进程，进程不重启就还是旧字节码。

## 最小修复

```bat
set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
node node_modules\electron\install.js
```

要点：镜像变量给 `@electron/get` 用，国内直连 GitHub Releases 会慢到像超时。**把这两行固化进启动脚本**，用 `if not exist node_modules\electron\dist\electron.exe` 做自愈判断，而不是写进文档等人执行——写进文档的那次一定会被跳过。主进程/preload 改动的验收前必须完整杀掉并重启应用。

## 验证记录

- [x] 格式化或静态检查：不适用（未新增源码）
- [x] 类型检查或编译：`tsc --noEmit` 通过
- [x] 单元、集成或端到端测试：不适用
- [x] 构建：`vite` dev 起来，端口 LISTENING 确认
- [x] 启动或手动回归：重启后窗口标题出现，截图确认渲染到主界面（进程存在不算证据）

## 可复用规则

1. 本地部署 Electron 工程后，**先量 `node_modules/electron/dist/<二进制>` 是否存在**，再启动；`npm install` 的退出码证明不了这一步。
2. 主进程或 preload 改过，判「有没有生效」之前先确认进程是新起的（比对 PID 或启动时间），别把旧进程的行为当成新代码的结果。
3. 适用：任何本地 clone 的第三方 Electron 工程。不适用：纯 web 运行时；已用 `electron-builder` 打包安装的正式客户端。

## 适用范围与不适用范围

- 适用：开发模式下从源码跑 Electron 桌面端；Windows/npm 11 组合。
- 不适用：Linux/macOS 上未复现（不排除同样存在）；`electron` 由全局安装提供的场景。

## 剩余风险

未查明 postinstall 被跳过的确切原因（npm 配置、还是脚本执行策略），因此每次新克隆都要按上面的判据自查，不能假设修好过就永久好。

## 关联

- 相关记录：[[03-通用/03-调试与验证/踩坑-WallpaperEngine接管桌面时注册表壁纸是过期图且素材藏在scene.pkg|Wallpaper Engine 当前壁纸只能问 WebAPI，素材在 scene.pkg]]（同一部署任务里发现的取数坑。原链接指向改名前的旧名，2026-11-15 重连）
- 相关分类：`03-通用/03-调试与验证`
- 相关代码、命令或文档：本次落位在 `D:\_整理\03-源码仓库\`（工程目录 + 同名启动器目录，启动脚本内含上述自愈判断）
