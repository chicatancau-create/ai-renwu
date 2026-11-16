---
title: "反向 smoothstep 在 ANGLE 吐 NaN，经 Bloom 放大成整帧黑"
date: 2026-11-15
domain: frontend
category: 01-前端/03-JavaScript与TypeScript
status: verified
severity: high
stack: [Three.js, WebGL2/GLSL ES 1.0, EffectComposer, UnrealBloomPass, ANGLE]
tags: [踩坑, GLSL, NaN, 后处理]
---

# 问题：合成链输出整帧纯黑，直连渲染却正常

## 一句话结论

GLSL 的 `smoothstep(edge0, edge1, x)` **在 edge0 >= edge1 时是未定义行为**，ANGLE 上会吐 NaN；
单个 NaN 像素只是小黑块，但 **UnrealBloomPass 的亮度提取 + 可分离模糊会把 NaN/Inf 沿 mip 链扩散**，
加性合成回主缓冲后整帧变 NaN → 显示为纯黑。

## 触发条件与影响

- 项目或功能：three.js 单文件页面，后期链 RenderPass → GTAO → Bloom → OutputPass(AgX) → grade → SMAA
- 环境与版本：three r169、WebGL2、Chromium/ANGLE（Windows）
- 触发条件：为表达"越小越亮"写降序阈值，如 `smoothstep(0.85, 0.03, depth)`；
  以及 `1.0/length(...)`、`x/(sin(t)/k)` 这类可能 0/0 的除法
- 影响范围：整帧不可用；且**关掉 bloom 就有画面**，容易被误判成"bloom 参数没调好"而反复调参

## 复现步骤

1. 前置条件：一个含 Bloom 的 composer 链，场景里有产生 NaN 的着色器
2. 操作或命令：逐 pass 开关截图对比
3. 预期结果：Bloom 只是让亮部发光
4. 实际结果：
   - `RenderPass` 单独 → 有画面；`+OutputPass` → 有画面；`+grade` → 有画面；`-Bloom` → 有画面；**全开 → 全黑**
   - `bloomPass.strength = 0` → 画面恢复（等于不再叠加那层脏数据）——这条是决定性判据

## 证据

- 逐 pass 二分的截图序列（RenderPass / +Output / +grade / -bloom / 全开）
- 按材质类别二分：把 `material.onBeforeCompile !== THREE.Material.prototype.onBeforeCompile`
  的网格全部隐藏后画面恢复 → 锁定到注入材质；再逐个恢复定位到具体着色器
- 页内 `readPixels` 均值：全开时 mean=0，关 bloom 时 mean≈105

## 根因分析

- 已确认的根因：① 降序 `smoothstep` 未定义 → NaN；② `caustic()` 里 `sign(0.0)` 返回 0，
  导致"除零守卫"实际写成 `x/0` → NaN；③ 折射路径长度未夹紧 → `exp(-k*1e9)` 把 G/B 打死（大片红黑）
- 排除过的假设：阴影贴图（关掉 castShadow 无变化）、GTAO（关掉仍黑）、色彩空间/色调映射（直连渲染正常）、
  单个物体的几何 NaN（按物体隐藏定位不到，因为同一材质挂在多个物体上）
- 问题归属：本次修改引入

## 最小修复

1. 降序阈值一律改写成 `1.0 - smoothstep(小, 大, x)`，永远 edge0 < edge1。
2. 除法前 `max(abs(d), eps)` 且**自己保号**（`d < 0 ? -eps : eps`），不要依赖 `sign()`。
3. 解析求交的命中距离夹紧，并对退化情形（交点在轴上、`length(xz)≈0`）单独保护。
4. 自定义 ShaderMaterial 输出前做可移植的 NaN 兜底：

   ```glsl
   float s = c.x + c.y + c.z;
   c = ( s != s ) ? vec3(0.0) : max(c, vec3(0.0));   // NaN != NaN；max() 不吞 NaN
   ```

5. `onBeforeCompile` 注入标准材质时，注入点选 `#include <dithering_fragment>`（该 shader 最后一步）。
   渲染进 RenderTarget 时 three **跳过 tone mapping 与色彩空间转换**，所以那里相加的是线性 HDR 值；
   同时必须设 `material.customProgramCacheKey`，否则不同注入变体会共用已编译程序。

## 验证记录

- [x] 静态检查：提取模块脚本 `node --check` 通过
- [x] 端到端回归：修复后全链 mean 0 → 104.8，截图正常，异常收集为空
- [x] 复测三档光照 + 画质三档 + 窗口缩放 + 拖拽/滚轮：无报错
- [ ] 单元测试 / 构建：本任务无这些环节，未执行

## 可复用规则

写 GLSL 时**禁止出现 edge0 >= edge1 的 smoothstep**（评审时直接搜 `smoothstep(` 看两个常数顺序）。
症状为"整帧黑/整帧白且关掉某个 blur 就恢复"时，**先按 pass 二分，再按材质二分**，
不要先调参；判据记住一条：`strength=0` 能恢复＝输入里有 NaN/Inf，不是参数问题。
例外：只用标准材质、无自定义注入时，此路径基本不会触发。

## 适用范围与不适用范围

- 适用：任何 WebGL/GLSL + 模糊类后期（Bloom、DOF、SSAO 合成）；three `onBeforeCompile` 注入
- 不适用：Canvas2D、CSS；未在其他 ANGLE 后端（Vulkan）/原生 GL 复测，但"未定义"是规范级问题，
  换后端只会改变表现形式，不会变安全

## 剩余风险

- 不同驱动对 `edge0>=edge1` 的实现不同，可能表现为 0、1 或垃圾值而非 NaN，届时故障形态会变（仍是同一个 bug）。
- NaN 兜底只覆盖自定义 ShaderMaterial 出口；标准材质的注入点若产生 NaN，仍需靠根因修掉。

## 关联

- 相关记录：[[踩坑-隐藏页挂起rAF且截图字节数判不了黑屏-WebGL取证]]
- 相关分类：03-通用/03-调试与验证
- 相关代码：`E:\fullstack-code\Web\webgl自学\浮空树脂小岛.html`（`GLSL_CAUSTIC`、`applyUnderwater`、水面/树脂壳着色器）
