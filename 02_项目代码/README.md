# 02_项目代码 · 项目索引

> 本目录放**可复用/在用的工具项目源码**（区别于 01_任务归档 的一次性任务产出）。共 4 个项目。
> 白名单入库：vslang-probe / preview-fixture / dsh-preset-switcher / gemini-pack（见根 .gitignore）。

## ⚠ 活体依赖（搬动/删除前必查）
- **dsh-preset-switcher** 被 DSH profile 以 `link:` 方式引用：`C:\Users\Admin\.dsh\profiles\desktop\package.json` 指向本目录，`node_modules` 内是 Junction。**不可移动/删除/改名**，否则 DSH 桌面端预设切换插件失效。

## 项目清单

| 项目 | 是什么 | 入口 / 关键件 | 状态 |
|---|---|---|---|
| dsh-preset-switcher ⚠ | DSH 插件：在已开始的会话里切换智能体预设（模式）。`@local/dsh-preset-switcher` v1.0.0 | package.json（exports index.js/client.js/locale/icon；dsh.bundle.patch=cordis.patch.yml；client web immediately） | 活体，被 desktop profile link: 引用 |
| gemini-pack | Gemini 双仓库数据包构建器 | `_build_pack.py`（构建入口）；00/01/02-*.md 为派生快照（gitignore 排除） | 工具 |
| preview-fixture | ppt-master svg_editor 的预览夹具 | `svg_output\slide_01.svg`；配套 `脚本库\08_实验与预览\preview-fixture-test.ps1`（端口 8765，server 在 D:\QoderToolkit\ppt-master\scripts\svg_editor\server.py） | 夹具；测试脚本解释器 D:\PyCharm\Python\python.exe 已消失，下次用需换解释器 |
| vslang-probe | VSLANG 1033 是否把 MSVC 诊断切成英文的 A/B 实验 | bad.cpp / varA.bat / varB.bat / logA.txt / logB.txt | 实验夹具；结论见手册 `03-通用\03-调试与验证\踩坑-VSLANG1033未把MSVC诊断切成英文.md` |

## 备注
- KaihongOS 项目**尚未建**：安装镜像在 `H:\下载\KaihongOS桌面版（x86）6.1试用版安装镜像包\`，需要时再立项。
- 本目录只放项目源码；项目相关的一次性报告/证据仍归 01_任务归档 对应任务夹。
