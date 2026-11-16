# JavaScript 与 TypeScript

适合记录运行时行为、异步、类型系统、模块、数据转换和浏览器 API 问题。

## 记录

- [[踩坑-反向smoothstep吐NaN经Bloom放大成整帧黑-WebGL]]（verified，2026-11-15）— GLSL 里 `edge0 >= edge1` 的 smoothstep **是未定义行为**，ANGLE 上吐 NaN；单像素 NaN 只是黑块，但进 UnrealBloomPass 的 mip 模糊会扩散成**整帧黑**（`strength=0` 或关掉 bloom 就恢复＝判据）。降序阈值一律写 `1.0 - smoothstep(小,大,x)`；`sign(0.0)==0` 让除零守卫失效；定位要按**材质类别**二分（`onBeforeCompile !== Material.prototype`），按单个物体二分常定位不到

