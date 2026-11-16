---
title: "本地大模型「到底走没走 GPU」：应用面板显存 0%、任务管理器没 GPU 列都不是证据"
date: 2026-11-15
domain: common
category: "调试与验证"
status: verified
severity: medium
stack: ["牧羊人 Herdsman v0.6.7", "llama.cpp", "NVIDIA RTX 5070 Laptop", "Windows 11", "PowerShell"]
tags: ["显存", "GPU取证", "nvidia-smi", "Get-Counter", "任务管理器", "监控读数不可信", "本地大模型"]
---

# 问题：面板显示 GPU 0% / VRAM 0%，模型其实满速跑在显存里

> 只有复现、定位、修复、验证都完成后才是 `verified`。本条四项均已完成，见「验证记录」。

## 一句话结论

**判「走没走 GPU」只认两条硬判据**：① 启动进程命令行里有没有 `-ngl`；② 那个 PID 占了多少
专用显存。应用自带面板和任务管理器的默认视图都会**假报 0**，而且假得非常自信。

## 触发条件与影响

- 项目或功能：本地跑 llama.cpp 系模型（宿主是牧羊人 Herdsman），要判断权重是在显存还是内存
- 环境与版本：Windows 11 + RTX 5070 Laptop 8GB + 牧羊人 v0.6.7-0-g5a98109c
- 触发条件：宿主「运行中心」的显存数据源选了「适配器计数器」；或任务管理器进程页没勾 GPU 列
- 影响范围：会误判成「GPU 完全没用上」，从而去乱改配置、重装运行时，甚至放弃本地部署

## 复现步骤

1. 前置条件：模型已启动并确认全部层进了显存（命令行含 `-ngl 99`，日志有 `offloaded 65/65 layers to GPU`）
2. 操作或命令：
   - 看牧羊人 运行中心 → 概览
   - 看任务管理器 进程 页
   - `nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.free --format=csv,noheader`
   - `powershell -c "(Get-Counter '\GPU Process Memory(*)\Local Usage').CounterSamples | ? InstanceName -match 'pid_<PID>'"`
3. 预期结果：三处都说显存被占了
4. 实际结果：
   - 面板显示 `GPU 0%`、`VRAM 已用 -- (0%)`、`专用显存 --`（**连数值都是两个减号**＝没取到）
   - 任务管理器默认表头只有 `CPU/内存/磁盘/网络`，**根本没有 GPU 列**；
     右上角那个 `0%` 是**网络**列的分组表头，被当成 GPU 是纯误读
   - nvidia-smi 报 `利用率 97%`、`已用 7637 MiB / 空闲 255 MiB`（空闲时确实 0%）
   - Get-Counter 报该 PID `Local Usage 5980 MB` —— 与 nvidia-smi 一致

## 证据

```
牧羊人面板（同一时刻）: GPU 0% | VRAM 已用 -- (0%) | 专用显存 -- | 数据源=适配器计数器
nvidia-smi            : 97 %, 7637 MiB used, 255 MiB free
Get-Counter           : pid_16380_luid_..._phys_0  5980 MB
llama-server 日志      : load_tensors: offloaded 65/65 layers to GPU
命令行                 : ... --device CUDA0 -np 1 -ngl 99 --cache-type-k q8_0 ...
```

另两条配套判据（也验证过，但**不如上面两条可靠**，只当辅助）：

- 进程工作集：GPU 模式约 2~3GB，CPU 模式 9~10GB。**但会涨**——llama.cpp 的
  `--cache-ram 8192` 是最大 8GB 的 RAM 前缀缓存，实测同一 GPU 模式的进程从 2.1GB 慢慢涨到 3.7GB。
  所以「内存占好几个 G」不能用来推翻「它在 GPU 上跑」。
- 生成时的 SM 时钟与功耗：空闲 22W，加载后 50~114W、`clocks.sm` 拉到 ~3000MHz。

## 根因分析

- 已确认的根因：
  1. 宿主的显存读数走 DXGI 适配器计数器；本机（独显直连形态）取不到该计数器，
     于是**返回空值并把空值显示成 `--` 和 0%**——面板没坏，是数据源本来就没有数。
  2. 任务管理器没被配置成显示 GPU 列，用户把「网络 0%」当成了 GPU。
- 排除过的假设：模型是否真在 CPU（已排除——offload 日志 + 每进程显存 + 生成时 97% 利用率三条独立证据）
- 问题归属：环境或依赖（宿主监控实现 + 系统默认视图），不是本次修改引入

## 最小修复

不改程序，只改**取证手段**：

1. 判走没走 GPU，固定用这两条命令（PID 从 `Get-CimInstance Win32_Process` 取）：
   ```powershell
   # ① 启动参数里有没有 -ngl（注意宿主可能启动的是包装层，真身在 llama-server-real.exe）
   Get-CimInstance Win32_Process -Filter "Name='llama-server-real.exe'" | % { $_.CommandLine }
   # ② 该 PID 的专用显存占用
   (Get-Counter '\GPU Process Memory(*)\Local Usage').CounterSamples |
     ? InstanceName -match "pid_$PID" | % { $_.InstanceName + '  ' + [int]($_.CookedValue/1MB) + ' MB' }
   ```
2. 想在任务管理器里直接看：进程页右键表头 → 列选择 → 勾「**专用 GPU 内存**」，
   或在 性能 → GPU → 看「GPU 内存」曲线。
3. 利用率必须在**正在生成时**采样；空闲采样看到 0% 是正常的，不能当结论。

## 验证记录

- [x] 复现：模型满 offload 时面板仍显示 VRAM `-- (0%)`、GPU 0%（同屏截图留存）
- [x] 取证一致性：`Get-Counter` 每进程显存 5980 MB 与 nvidia-smi 总占用差值吻合
- [x] 生成中采样：连续 6 次采样 `utilization.gpu` = 97~99%，解码 42 tok/s
- [x] 反例排除：`-ngl 0` 同配置解码 0.64 tok/s、显存几乎不涨，两条判据同步变化
- [ ] 未覆盖：独显被其他程序大量占用时面板是否仍返回空值（未单独验证）

## 可复用规则

**任何「某资源有没有被用上」的判断，先问：这个读数是从哪个计数器来的、取不到时会显示成什么。**
显示成 `--`、空、0% 三选一的，一律视为「无数据」而不是「用量为 0」。
改用一个能按进程归属的读数（PDH 计数器 / nvidia-smi / 进程命令行）作证据，并在**负载进行中**采样。

## 适用范围与不适用范围

- 适用：本机所有把 DXGI/PDH 计数器当监控源的应用内嵌面板；任务管理器默认视图；任何
  「面板显示 0 但程序行为正常」的资源归属判断
- 不适用：确实没有资源被占用的情况（`nvidia-smi` 与 `Get-Counter` 都为 0 且命令行里确实没相关参数）；
  多 GPU 机器需要按 `luid`/`phys_N` 分别看，别只看第一行

## 剩余风险

- 8GB 显存跑满后每进程显存与系统显示可能一起失真（进共享显存），此时速度会突然掉一个量级；
  这与「没走 GPU」是两回事，要用吞吐 + `clocks_throttle_reasons` 一起判。
- 若宿主将来实现了显存计数器兜底，本条的面板部分会失效（进程命令行 + Get-Counter 两条仍然成立）。

## 关联

- 相关记录：[[踩坑-笔记本功耗封顶让同一配置吞吐差十倍-tok每秒不能当基线]]（同一项目的另一条取证纪律）、
  [[踩坑-AI面板连接失败耗时1ms是没填密钥而非网络]]（同类「读数误导」的判据思路）
- 相关分类：[[03-通用/03-调试与验证/README|调试与验证]]
- 相关代码、命令或文档：本项目部署记录在 `D:\Models\Ternary-Bonsai-2-27B-gguf\部署交接说明.txt`
  第一/二/六节（含实测数据表与显存不足时的处置阶梯）
