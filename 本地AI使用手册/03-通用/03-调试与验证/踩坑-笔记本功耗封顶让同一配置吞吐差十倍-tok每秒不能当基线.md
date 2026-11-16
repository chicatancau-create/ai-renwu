---
title: "笔记本跑本地大模型：同一配置吞吐能差 10 倍，拿 tok/s 当基线会误判成配置坏了"
date: 2026-11-15
domain: common
category: "调试与验证"
status: verified
severity: medium
stack: ["llama.cpp", "NVIDIA RTX 5070 Laptop", "Windows 11", "nvidia-smi"]
tags: ["吞吐基线", "功耗封顶", "SW Power Cap", "笔记本", "A/B测试", "降频", "本地大模型"]
---

# 问题：刚测好 42 tok/s，两小时后同一配置只有 4 tok/s，配置完全没变

> 四项（复现/定位/修复/验证）均完成，见「验证记录」。

## 一句话结论

**笔记本的 tok/s 不是配置的属性，是当下供电状态的属性。**
这台机器同一天同配置实测 4.3 → 15 → 29 → 42 tok/s，差别全部来自 GPU 功率封顶
（`clocks_throttle_reasons.active = 0x400` = SW Power Cap）。
要比较两个配置，必须**同一电源状态下同时段 A/B**，不能拿历史数字当基准。

## 触发条件与影响

- 项目或功能：本地 27B 模型（llama.cpp + 8GB 显存笔记本）性能调优与排障
- 环境与版本：RTX 5070 Laptop 8GB，Windows 11，电池 + 充电器混用一整天
- 触发条件：用「上一次测到的 tok/s」判断「这次是不是配坏了」
- 影响范围：整天的误判。一度据此怀疑自己把一个 12.8GB 模型文件的改写改坏了、
  又怀疑配置被宿主回写覆盖——两个假设都是错的

## 复现步骤

1. 前置条件：模型在跑，配置完全不动
2. 操作或命令：连跑 2~3 轮同一 prompt，每轮同时采样
   ```
   nvidia-smi --query-gpu=power.draw,clocks.sm,clocks.mem,clocks_throttle_reasons.active,temperature.gpu --format=csv,noheader
   ```
3. 预期结果：吞吐稳定
4. 实际结果：吞吐随功率走。同一天两组硬数据：

| 时点 | 电源 | 生成中功率 | 解码 tok/s |
|---|---|---|---|
| 插电 | AC | 99~114 W | **42** |
| 电池 | BatteryStatus=2 | 67 W | 14 |
| 电池+100%电量 | PowerAC=True 但被限 | 50 W | 4.3 |

## 证据

**同时段 A/B（决定性）**——同一时刻、同一台机器、只差模型文件，用完全相同的参数：

```
A 原件   解码 15.40 / 15.60 tok/s   功率 73 / 76 W   sm 3000MHz  mem 12001MHz  throttle 0x400
B 新件   解码 29.40 / 29.42 tok/s   功率 106 / 107 W  sm 2955MHz  mem 12001MHz  throttle 0x400
```

- 电池下的报错链：`BatteryStatus=2`（在用电池）与 `PowerAC=True` 同时出现——
  插着电但充到 100%，适配器供不出峰值功率，于是 GPU 被软件封顶。
- 不是热降频：全程 `temperature.gpu` 只有 51~52℃；`clocks.max.sm` 3090 而实测 2167~3067。
- 判据不是猜的：`clocks_throttle_reasons.active = 0x0000000000000400` 直接写明 SW Power Cap。

## 根因分析

- 已确认的根因：笔记本 GPU 可用功率随电源/电量/适配器余量动态变化，
  llm decode 是带宽与频率敏感的，功率一封顶吞吐就断崖式下跌。
- 排除过的假设（都是被这条数据打掉的）：
  1. 「我改坏模型文件了」→ 同时段 A/B 新件反而更快（29.4@106W vs 15.4@73W），排除
  2. 「宿主把配置回写覆盖了」→ 命令行里 `-ngl 99` 一直存在，排除
  3. 「热降频」→ 温度 52℃，排除
  4. 「显存溢出进共享内存」→ `clocks.mem` 两跳一致 12001MHz，排除
- 问题归属：环境（供电），不是修改引入

## 最小修复

不是修配置，是改**测量纪律**：

1. 测吞吐固定连跑 ≥3 轮并**记录每轮的 power.draw 与 throttle 原因**；
   第一轮通常偏低（GPU 频率还没爬上来、前缀缓存没热），当预热丢掉。
2. 比较两个方案只用「同一时段交替跑」的 A/B，不跨时间比历史数字。
3. 判「突然变慢」先看电源三件套，再动配置：
   ```
   powershell -c "(Get-CimInstance Win32_Battery).BatteryStatus; (Get-CimInstance -Namespace root/wmi -ClassName BatteryStatus).PowerOnline"
   nvidia-smi --query-gpu=power.draw,clocks_throttle_reasons.active,temperature.gpu --format=csv,noheader
   ```
4. 写文档/给人报数时，一律带上当时的功率或电源状态，否则数字会被当成基准。

## 验证记录

- [x] 复现：同配置在不同电源状态下 4.3 / 14 / 29 / 42 tok/s，逐次记录功率与 throttle
- [x] 定位：`0x400` SW Power Cap 全程存在；温度、显存频率均排除
- [x] A/B 验证：同时段两文件对照，新件 29.4@106W > 原件 15.4@73W，证明「变慢」与改动无关
- [x] 预热效应：第 1 轮 4.19、第 2 轮 14.66、第 3 轮 14.07 tok/s（同一电池状态下也分层）
- [ ] 未量化：各适配器功率档对应的 tok/s 曲线（没做扫频实验，只做了对照）

## 可复用规则

**性能数字必须与「当时的资源上限」绑定记录，否则不可比较。**
任何「昨天还好、今天慢十倍」的先跑一次电源/限频取证再改配置；
在笔记本上，这一条能省掉一整轮错误归因。

## 适用范围与不适用范围

- 适用：游戏本/轻薄本上跑本地 LLM、GPU 转码、大模型推理压测；任何吞吐敏感的同机对比
- 不适用：台式机固定供电（仍建议记录功率，但不会出现本例的 10 倍摆动）；
  CPU 推理为主的任务（受另一套功耗策略约束）

## 剩余风险

`PowerAC=True` 与 `BatteryStatus=2` 并存说明这两个字段不能单独用来判「有没有插电」，
必须两条一起看，且真正的原因只能由 `clocks_throttle_reasons` 定性。

## 关联

- 相关记录：[[踩坑-应用面板显存0%与任务管理器无GPU列-判走没走GPU的两条硬判据]]（同一项目的取证方法）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关文档：`D:\Models\Ternary-Bonsai-2-27B-gguf\部署交接说明.txt` 第十一节末「重要修正」段
