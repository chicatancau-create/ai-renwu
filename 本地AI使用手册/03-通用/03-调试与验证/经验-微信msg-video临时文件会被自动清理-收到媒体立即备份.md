---
title: 微信 msg\video 临时文件会被自动清理——收到媒体立即备份
date: 2026-11-21
domain: common
category: 03-调试与验证
status: verified
severity: medium
stack: [wechat, windows, ffmpeg]
tags: [微信, 临时文件, 媒体备份, 文件消失]
---

# 微信 msg\video 临时文件会被自动清理——收到媒体立即备份

## 一句话结论

微信 PC 版 `…\xwechat_files\<wxid>\msg\video\<YYYY-MM>\<hash>.mp4` 是临时缓存，会被自动清理（实测同一天 20:37 还能 ffprobe、20:52 已不存在）；拿到用户微信媒体后**第一步备份原件或抽音轨到任务目录**，再做分析/剪辑。

## 触发条件与影响

- 用户从微信转发/附件给出的视频路径指向 msg\video 月目录。
- 影响：分析做到一半源文件消失，ffmpeg/库报 `No such file or directory` / `FileNotFoundError: 找不到 <path>`；若未提前备份，素材永久丢失（聊天里可能仍可重发）。

## 复现步骤

1. 2026-11-21 20:37 ffprobe 成功读取 `E:\微信聊天文件\xwechat_files\wxid_hv1i7l8cyl6p22_5f9b\msg\video\2026-11\8c2cc3c48c1ed2eebdb2818927004a32.mp4`（86.6s）并抽出 wav。
2. 20:52 同路径 ffmpeg 报 Error opening input: No such file or directory；目录列表与全库 glob `**/8c2cc3c4*` 均无结果（同批另一视频 d346edb8… 也消失）。
3. 目录里只剩 jpg/_thumb.jpg 与更早日期的 mp4 → 清理针对近期临时视频。

## 证据

- 任务档案 `G:\AIrenwu\01_任务归档\2026-11-20_平静vlog剪辑\02_证据日志\`：silence_narr.txt、asr_narr.srt（源消失前产出）。
- 备份存活：`D:\AI-Tool-State\vlog-mint\素材\wechat_narr.wav`（16kHz 单声道）——v2 精剪旁白全靠它完成。

## 根因分析

微信对 msg\video 临时缓存有自动清理策略（触发条件未确证：疑似容量/时限/播放后清理）；_thumb.jpg 与 jpg 预览保留更久。不要假设该路径长期有效。

## 最小修复

收到媒体立即：`Copy-Item <原路径> D:\AI-Tool-State\<任务>\素材\`；只要声音则 `ffmpeg -i <原路径> -vn -acodec copy <任务>\素材\x.m4a`（无损）或按需 wav。后续脚本一律引用备份路径。

## 验证记录

- [x] 源消失后仅凭备份 wav 完成 17 块旁白精剪草稿（平凡的一天_精剪，97.01s）。
- [ ] 高音质原件备份未做成（源已删）——教训即本条。

## 可复用规则

- 微信/ QQ 等 IM 的 msg 临时目录一律视为「易失存储」：先备份再分析。
- 备份音质取舍：抽音轨做 ASR 用 16k wav 够；若可能进成片，抽 `-acodec copy` 保留原音质。

## 适用范围与不适用范围

- 适用：微信 PC 版 xwechat_files 结构（本机 2026-11 实测）。
- 不适用：用户主动「另存为」到普通目录的文件；其他 IM 未测。

## 剩余风险

清理触发条件未确证，无法预测存活时长；唯一可靠做法是立即备份。

## 关联

- [[经验-CapCut国际版草稿自动化-pycapcut建草稿与vosk离线字幕]]（本轮消费该备份的任务）
