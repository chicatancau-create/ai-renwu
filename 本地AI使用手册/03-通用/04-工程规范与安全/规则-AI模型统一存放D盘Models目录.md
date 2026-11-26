---
title: 规则-AI模型统一存放D盘Models目录
date: 2026-11-22
domain: common
category: 04-工程规范与安全
status: verified
severity: medium
stack: [windows, vosk, faster-whisper, gguf]
tags: [模型管理, 目录规范, D盘]
---

# 规则-AI模型统一存放D盘Models目录

## 一句话结论

用户指定 `D:\Models` 为全机唯一模型目录：**所有 AI 模型权重只放这里、只从这里加载**；安装包 zip 归 `D:\Models\_archives\`（用户 2026-11-22 m01482 原话授权，长期有效）。

## 触发条件与影响

任何任务下载/解压/引用模型权重时。违反后果：模型散落任务目录（本例曾散在 `D:\AI-Tool-State\vlog-tools\`），换任务找不到、重复下载、C 盘膨胀。

## 复现步骤（本轮迁移实例）

1. 盘点：`D:\AI-Tool-State\vlog-tools\` 下 vosk-model-small-cn-0.22、vosk-cn-extract\model-cn、fw-large-v3 三个模型目录 + 3 个 zip；用户自有模型已在 D:\Models（Ternary-Bonsai-2-27B-gguf、qwen2.5-0.5b gguf）。
2. 同卷 Move-Item 瞬时改名迁入：`D:\Models\vosk-model-small-cn-0.22`、`D:\Models\vosk-model-cn-0.22`、`D:\Models\faster-whisper-large-v3`；zip → `D:\Models\_archives\`；空壳 vosk-cn-extract 确认空后删除。
3. grep 全库旧路径改引用：asr_to_srt.py 默认 MODEL_DIR、fw_transcribe.py MODEL、手册安装命令、三份任务报告。
4. 验证：两脚本从新路径加载跑 TTS 自测音频——vosk 10 词 1 条字幕、whisper「今天天气真好,阳台的薄荷长出了新芽。」整句正确。

## 证据

- `G:\AIrenwu\01_任务归档\2026-11-20_平静vlog剪辑\02_证据日志\verify_models_move_vosk.srt`、`verify_models_move_fw.json`（迁移后加载验证）。
- 迁移前后目录清单见本轮会话记录（m01482 起）。

## 根因分析

此前无模型目录规范，下载顺手落在工具目录；用户既有 D:\Models 习惯（gguf 部署项目）未成文。

## 最小修复

成文规则（本条 + 全局记忆 `rule-models-store-in-d-models.md`）+ 脚本默认路径改指 D:\Models + 存量迁移。

## 验证记录

- [x] 三模型目录与 zip 迁入 D:\Models，vlog-tools 只剩 pylibs。
- [x] asr_to_srt.py / fw_transcribe.py 新默认路径加载并识别正确。
- [x] 手册/报告旧路径引用已改（grep 复核无残留 vlog-tools 模型路径）。

## 可复用规则

1. 新模型下载/解压直接落 `D:\Models\<模型名>\`；zip 留 `D:\Models\_archives\`。
2. 脚本里模型路径写 D:\Models 默认值，环境变量（如 VOSK_MODEL）仅作临时覆盖。
3. 迁移用同卷 Move-Item；迁完 grep 旧路径清引用；空壳目录确认空再删。
4. 不完整下载包（如 383MB 的 vosk-model-cn-0.22.zip，完整应 1.3GB）标注可删，不混入可用模型。

## 适用范围与不适用范围

适用：本机一切任务级 AI 模型权重与安装包。不适用：应用自带内置模型（CapCut 安装目录内、DSH runtime 内）——那是软件组成部分，不动。

## 剩余风险

旧会话/旧文档里仍可能出现旧路径字样（历史证据保留不改）；_archives 内不完整 zip 待用户决定删除。

## 关联

- 全局记忆：`D:\Skills\global-memory\rule-models-store-in-d-models.md`
- [[经验-CapCut国际版草稿自动化-pycapcut建草稿与vosk离线字幕]]（安装命令已改 D:\Models）
- [[规则-任务区与手册一体化联动]]