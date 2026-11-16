# 构建与工程化

适合记录包管理器、依赖、脚本、环境变量、打包、代码规范和开发工具链问题。

## 记录

- [[踩坑-HBuilderX-Vue3项目根目录缺index.html致停止运行]]（verified，2026-11-02）— Vue 3 的 HBuilderX 工程根目录必须有 `index.html` 且入口指向 `/main.js`；清理构建产物时不要误删，Vue 2 无此文件属正常。
- [[踩坑-模块URL失败被负缓存且importmap不支持fallback数组-CDN单文件]]（verified，2026-11-15）— Chromium 里 `"three": ["A","B"]` **整条规则失效**（报 Failed to resolve specifier），改字符串立刻好；同一 URL 失败一次就被**负缓存**，同 specifier 重试必然再失败 → 兜底只能换 URL；但 addon 内部 `import 'three'` 走 importmap，**核心换源会得到两份 three 实例**；同步 XHR 探测镜像在本机因 DNS 超时把首屏拖慢十几秒，属反效果

- [[踩坑-npm-install不跑electron-postinstall且改主进程须重启-Electron]]（verified，2026-11-15）— `npm install` 退出码 0 也可能**根本没下 electron 二进制**（唯一判据是 `dist/electron.exe` + `path.txt` 在不在）；补法 `ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ node node_modules/electron/install.js`，并且要把它写成启动脚本里的 `if not exist` 自愈判断，**不要**只写进文档——写进文档的那次一定被跳过。主进程/preload 改动 Vite HMR 接不住，验收前先确认进程是新起的。
