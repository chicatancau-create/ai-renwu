---
title: "Wallpaper Engine 接管桌面时，注册表里的壁纸图是过期无关内容；当前场景只能问它的 WebAPI，素材在 scene.pkg 里"
date: 2026-11-15
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Windows, Wallpaper Engine, Node]
tags: [壁纸取数, scene.pkg, WebAPI, 动态壁纸, 本机取证]
---

# 问题：想拿「用户桌面现在那张图」，注册表给的却是一张毫不相干的旧图

> `needs-review` 表示尚未完成验证；只有复现、定位、修复和验证都完成后，才改为 `verified`。

## 一句话结论

只要 `wallpaper64.exe` 在跑，`HKCU\Control Panel\Desktop\Wallpaper` 指向的 `TranscodedWallpaper` 就**不能当桌面现状用**（实测拿到的是另一张过期图）；「当前应用哪个壁纸」这个问题只有一个可信答案来源——Wallpaper Engine 自己的 WebAPI，而它默认是关的。素材本身编译进 `scene.pkg`，但可以按容器魔数流式扫出来。

## 触发条件与影响

- 项目或功能：需要把桌面壁纸接到应用里（封面、主题取色、视觉一致性校验）。
- 环境与版本：Windows 11 + Steam 版 Wallpaper Engine；桌面是 shader 场景壁纸。
- 触发条件：读注册表壁纸路径并把它当现状使用。
- 影响范围：整条功能建立在错误素材上；更隐蔽的是「图很暗所以是星空」这类自我说服会把错误前提带进后续设计（见关联记录）。

## 复现步骤

1. 前置条件：Wallpaper Engine 正在推一张银河星空场景。
2. 操作或命令：
   - `Get-ItemProperty 'HKCU:\Control Panel\Desktop'.Wallpaper` → `...\Themes\TranscodedWallpaper`
   - 打开该文件目视；
   - `netstat -ano | grep :34897` 探 WebAPI。
3. 预期结果：那张图就是桌面星空；或 WebAPI 可用。
4. 实际结果：图是**紫红色光环**，与桌面无关；`34897` 无监听，`curl` 直接 `connect refused` → WebAPI 是关的。

## 证据

- 素材定位：`F:\SteamLibrary\steamapps\workshop\content\431960\<id>\` 下 5 个场景全是 `scene.pkg` + `preview.gif|jpg`，无散图。用 preview 首帧拼 montage 目视比对锁定当前场景 id。
- 容器抽取：`scene.pkg` 158 MB，按 PNG/JPEG 魔数流式扫（4 MB 分块 + 4 KB 重叠，读 IHDR/SOF 拿宽高）能捞到内嵌全景贴图；实测 **145 ms** 扫完，抽出的 2048×1024 PNG 与人工定位偏移抽出的那份 **sha256 逐字节一致**（重写分块循环后复跑仍一致）。
- 代理无关性：Node 的 `http` 模块不读 `*_proxy` 环境变量，所以打 `127.0.0.1` 本机服务不会被系统代理劫持——这是这条链路能用普通 `http.get` 的前提。

## 根因分析

- 已确认的根因：`TranscodedWallpaper` 是 Windows 侧的转码快照，Wallpaper Engine 接管后不再按当前场景刷新它；WE 的当前场景状态只存在它自己的运行时里，对外只经 WebAPI 暴露，而该接口需要在设置里显式勾选「允许来自本地应用的远程请求」。

## 最小修复

1. 判「是不是 WE 在管桌面」：看 `wallpaper64.exe` 是否存在，存在就把注册表壁纸路径降级为「不可信快照」。
2. 拿现状一律问 WebAPI `GET http://127.0.0.1:34897/v1/wallpaper?index=0`；拿不到（端口不通）时**返回空并走回退路径**，不要猜。
3. 场景素材用容器扫描（魔数 + 头解析），不要试图找散图；按「等距圆柱 2:1 优先 + 面积上下限 + 单张字节上限」挑，过大的一律跳过。
4. 结果落进应用自己的内容寻址缓存，用源文件 mtime+size 做失效判断，比哈希整个 158 MB 包快得多。

## 验证记录

- [x] 格式化或静态检查：不适用
- [x] 类型检查或编译：`tsc --noEmit` 通过
- [x] 单元、集成或端到端测试：容器扫描器新增 4 项合成用例全过（PNG/JPEG 头解析、2:1 优先、低于下限要跳过、无图返回 null）
- [ ] 构建：不适用
- [x] 启动或手动回归：**端到端已取证**（用 mock 顶替 WebAPI，见上面规则 4）——mock 收到真请求、内容寻址资产落盘且摘要与手工抽取的 sha256 相同、截图确认壁纸层与星点心形都上屏。唯一未证的是真实 WE 返回的字段形态。

## 可复用规则

1. 动态壁纸程序在场时，任何「系统壁纸路径」都不能当桌面现状用；先证明接管者是谁。
2. 从二进制容器里取素材：魔数 + 头部解析 + 分块重叠扫描是可复用的通用手法，几百 MB 级容器百毫秒级完成，比整份读进内存稳。
3. 探本机服务端口用 `netstat` + 直连 `curl`，并确认没被系统代理改写（Node `http` 默认不读代理变量）。
4. **不该由你去改第三方应用的开关时，用 mock 顶替它的接口**，把自己这半边链路逐环取证证死，再把「真程序返回的字段形态」作为唯一遗留项交回用户。本次即如此：起一个占 34897 的服务只回答「当前场景是哪个」，答案指向机器上真实存在的场景目录，于是 scheme→容器扫描→内容寻址落盘→自定义协议→`<img>`→叠加层全部有证据，而用户的设置一点没动。
5. 适用：Windows + 第三方壁纸接管、需要从应用私有容器格式取嵌入资源。不适用：macOS/Linux 未测。

## 适用范围与不适用范围

- 适用：本机 Wallpaper Engine 场景；其他把资源打包进自定义容器的桌面应用同理。
- 不适用：Windows 原生静态壁纸（那时 `TranscodedWallpaper` 与真实壁纸关系另说，本轮未测）。

## 剩余风险

- **真实 WE 开着开关时返回的字段形态未取证**（mock 已覆盖其余全链）；尤其 `path` 是否真指向 project.json。
- WE 里热切换场景时，60 秒轮询窗口内会短暂显示旧素材；未测。
- 取不到 scheme 时桥**保留上一个资产而不是清空**（`if (!scheme) return currentAssetId`）：换壁纸前旧星空会留着。这是防闪的有意设计，但必须知道它存在。
- 用 preview 首帧目视认场景是**权宜判据**，WE 的 settings 里到底有没有「当前 scheme」键本轮没找到（`config.json` 内无该键，Roaming/Local 两处目录都不存在）。

## 关联

- 相关记录：[[规则-判断图片内容必须目视打开不能靠亮度尺寸统计]]、[[踩坑-npm-install不跑electron-postinstall且改主进程须重启-Electron]]
- 相关分类：`03-通用/04-工程规范与安全`
- 相关代码、命令或文档：`GET http://127.0.0.1:34897/v1/wallpaper?index=0`；WE 设置 → 常规 → 允许来自本地应用的远程请求
