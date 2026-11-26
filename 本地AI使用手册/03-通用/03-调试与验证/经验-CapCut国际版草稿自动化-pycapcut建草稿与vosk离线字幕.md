---
title: CapCut 国际版草稿自动化：pycapcut 建草稿 + vosk 离线字幕流水线
date: 2026-11-20
domain: common
category: 调试与验证
status: verified
severity: low
stack: [CapCut 9.8.0.4213, pycapcut 0.0.4, pyJianYingDraft 0.3.1, vosk 0.3.45, Python 3.12.14, ffmpeg 9.0.2]
tags: [CapCut, 剪映国际版, 草稿自动化, pycapcut, vosk, ASR, 字幕, vlog]
---

# CapCut 国际版草稿自动化：pycapcut 建草稿 + vosk 离线字幕流水线

## 一句话结论

本机 CapCut 国际版 9.8.0.4213 可用 **pycapcut 0.0.4**（pyJianYingDraft 的 CapCut 移植）在草稿目录直接生成含视频+字幕的草稿（文件级 + CapCut 首页识别已验证）；字幕用 **vosk 0.3.45 + small-cn 模型**离线识别（真实中文语音逐字命中已验证）；口语素材小模型几乎全错时换 **vosk-model-cn-0.22 大模型**（1.26GB，hf-mirror.com 镜像约 8MB/s，alphacephei 直连仅 850KB/s），识别质量可用。装库必须用自带 Python 3.12，别用 D:\PyCharm 的 3.15（无 vosk wheel 会挂死在源码编译）。

## 触发条件与影响

- 要用脚本/AI 替用户剪 CapCut（国际版）视频、批量加字幕、按镜头表生成草稿时。
- 选错库（pyJianYingDraft 面向国内剪映）或错解释器（3.15）会直接失败或挂起 >240s。

## 复现步骤（安装，全部零成本）

```powershell
# 1) 库装到 D 盘独立目录（不污染全局），用自带 3.12 + 阿里云镜像
& 'C:\Users\Admin\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' -m pip install --target D:\AI-Tool-State\vlog-tools\pylibs -i https://mirrors.aliyun.com/pypi/simple/ pycapcut pyJianYingDraft vosk
# 2) vosk 中文小模型（41.86MB，curl 下载，zip 用 Expand-Archive）
curl.exe -L -o D:\Models\_archives\vosk-model-small-cn-0.22.zip https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip
Expand-Archive D:\Models\_archives\vosk-model-small-cn-0.22.zip D:\Models\   # 用户规定：模型统一放 D:\Models（2026-11-22 m01482）
# 3) 运行时设 PYTHONPATH
$env:PYTHONPATH='D:\AI-Tool-State\vlog-tools\pylibs'
```

## 证据

- 探针草稿：`C:\Users\Admin\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\AI工具链自检\`（draft_content.json 31 键、draft_meta_info.json 37 键，tracks=[video×1, text×1]，duration=6000000µs，素材路径正确）。
- 脚本与自测输出：`G:\AIrenwu\01_任务归档\2026-11-20_平静vlog剪辑\03_工具脚本\{probe_capcut_draft.py, asr_to_srt.py}`、`02_证据日志\{asr_selftest.srt, asr_tts_selftest.srt}`。
- ASR 真实语音验证：SAPI TTS（Microsoft Huihui Desktop zh-CN）说「今天天气真好，阳台的薄荷长出了新芽。」→ vosk 识别 10 词逐字命中，SRT `00:00:00,090 --> 00:00:04,170`。

## 根因分析（选型与坑）

1. **pyJianYingDraft 面向国内剪映**：剪映 6+ 加密 draft_content.json（模板模式只支持 ≤5.9）；CapCut 国际版草稿不加密但结构不同（9.x 多时间线：根 draft_content.json 兼容态 + draft_meta_info.json + Timelines/）。pycapcut（github.com/GuanYixuan/pyCapCut）是专门移植，实测生成的草稿文件结构完整。
2. **Python 3.15 装 vosk 挂起**：无预编译 wheel → pip 落源码编译，>240s 无输出（job 已 kill）。自带 DSH Python 3.12.14 有 wheel，秒装。
3. **字体 path="D:" 不是 bug**：pycapcut text_segment.py:421 故意写占位路径（注释「字体占位路径，与花字的 C: 分开，避免解析路径时被错误拼接」），CapCut 按 resource_id 解析字体。FontType 枚举含免费中文字体（圆体/宋体/中黑体/快乐体/悠然体等，font_meta.py:138-169）。
4. **脚本 docstring 含 C:\Users 报 SyntaxError**：`(unicode error) 'unicodeescape' ... truncated \UXXXXXXXX escape`（\U 被当 unicode 转义）→ docstring 用 r"""。

## 最小修复（API 速查）

```python
from pycapcut import DraftFolder, TrackType, VideoMaterial, VideoSegment, TextSegment, FontType, trange_seconds
folder = DraftFolder(r"C:\Users\Admin\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
script = folder.create_draft("草稿名", 1080, 1920, fps=30)   # 自动铺 draft_meta_info.json
script.add_track(TrackType.video)
script.add_track(TrackType.text)
mat = VideoMaterial(r"素材.mp4")                              # pymediainfo 读时长，单位 µs
script.add_segment(VideoSegment(mat, trange_seconds(0, 6)))
script.add_segment(TextSegment("字幕", trange_seconds(0, 6), font=FontType.圆体))
script.save()                                                 # 写 draft_content.json
```

ASR：`python -X utf8 asr_to_srt.py <输入视频/音频> <输出.srt>`（ffmpeg 抽 16kHz 单声道 wav → KaldiRecognizer(SetWords=True) 逐词 → 按 16 字/0.6s 停顿断句 → SRT）。

## 验证记录

- [x] 三库 import 全 ok（PYTHONPATH=pylibs，3.12）。
- [x] 探针草稿文件级断言 PROBE OK（键数/轨道/素材路径/时长）。
- [x] ASR 静音素材 → 0 词正常；TTS 真实中文语音 → 逐字命中。
- [x] CapCut GUI 首页识别草稿：用户空闲时启动 CapCut，环境检测弹窗（「您的电脑可以流畅使用CapCut」）自动通过，首页「草稿」区列出「AI工具链自检」（截图 `G:\AIrenwu\01_任务归档\2026-11-20_平静vlog剪辑\02_证据日志\capcut_main.png`）。验证后 WM_CLOSE 关闭 CapCut 恢复原样。
- [ ] 双击草稿进编辑器看时间线渲染 —— **未执行**：正要双击时用户回到活跃状态（USER_ACTIVE），按 windows-gui-control 规则让路；留待下次空闲补验。

## 可复用规则

- 剪映系草稿自动化先分国内/国际：国内剪映→pyJianYingDraft（≤5.9 模板模式；11.x 加密可试 PyPI jianying-tool 的 videoeditor.dll 适配器）；CapCut 国际版→pycapcut。
- 装带 C 扩展的库（vosk 等）先确认解释器版本有 wheel；本机首选自带 3.12，pip 加阿里云镜像 + --target 独立目录。
- 大模型/素材下载用 curl.exe -L，zip 用 Expand-Archive（本机解包只有 WinRAR UnRAR）。
- 离线中文 ASR 验证不必找真人录音：SAPI TTS（Huihui zh-CN 已装）生成标准语音即可闭环自测。

## 适用范围与不适用范围

- 适用：CapCut 国际版 9.8.0.4213（本机实测版本）新建草稿、视频/文本/音频轨、离线字幕。
- 不适用/未证：CapCut 云草稿（com.lveditor.cloud.draft_* 目录结构未探）；特效未逐一实测；转场/音频轨/alpha 关键帧结构断言+ffmpeg 代理整片审查通过（v3），但 CapCut 编辑器内渲染未目视（首页识别已过）；国内剪映加密草稿。

## 剩余风险

- 首页已识别精剪草稿「有花有草_精剪」（2026-11-21，截图 `G:\AIrenwu\01_任务归档\2026-11-20_平静vlog剪辑\02_证据日志\capcut_home7.png`）；编辑器内打开被合成输入怪癖挡住（见下条），待真实鼠标或空闲重试。
- CapCut GUI 合成输入怪癖（2026-11-21 实测）：①菜单弹层是独立全屏 Qt 窗口，鼠标注入点击穿透无效，键盘方向键+回车可用（菜单打开后 DOWN×8+ENTER=返回首页，DOWN×7+ENTER=全局设置）；②首页草稿卡片对单击/双击注入、PostMessage WM_LBUTTONDBLCLK 均无反应，UIA 控件树为空（Qt/CEF 未暴露 accessibility）→ 首页开草稿只能真实鼠标；③编辑器主窗口的鼠标注入曾生效（播放/暂停、菜单按钮），怪癖集中在弹层与首页。
- GUI 脚本两个坑：①执行策略拒 unsigned .ps1 → `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`；②`$idle = & useridle.py` 收到的是行数组，`$idle -notmatch 'USER_IDLE'` 按元素过滤返回非空数组恒真 → 必须先 `-join ' '`。
- vosk 小模型无标点、专有名词易错，字幕须人工过一遍；嘈杂环境识别率未测。
- CapCut 升级可能改草稿结构，用前复核版本。

## v2 补充（2026-11-21 晚，《平凡的一天》重剪）

- 转场：`VideoSegment.add_transition(TransitionType.叠化, duration=800000)`（video_segment.py:602）→ materials.transitions 3 条结构 OK；叠化免费（transition_meta.py:53）。
- 音频轨：`AudioSegment(AudioMaterial(path), trange(target_start, dur), source_timerange=trange(src, dur), volume=…)` + `add_fade`（audio_segment.py:166）；**AudioMaterial 拒视频容器**（local_materials.py:218 有视频轨即 ValueError）→ 先 ffmpeg 抽音轨（`-vn -acodec copy` 得 m4a 无损，或 wav）。
- 旁白去停顿：ffmpeg `silencedetect=noise=-35dB:d=0.5` 拿静音区间，≥0.8s 停顿切块剔除、块间留 0.12s 气口；配合大模型 ASR 剔絮语块。
- plan 生成单位坑：累计函数返回 µs 而字幕偏移用秒，混加得 target start=base_us*1e6+offset（如 4000000296667）；make_plan 加断言 `0<=start<us(total)` 防再犯。
- 本机网络音源实测：commons.wikimedia.org 连接重置；incompetech.com 挂起；github.com/raw 302 后 raw.githubusercontent 挂起；pixabay 403（Cloudflare）；**codeload.github.com 整仓 zip 可用**（158MB 约 40s）。CC-BY 曲目发布简介必须带署名行。

## v3 补充（2026-11-21 夜，整片审查法）

- **不开 CapCut 也能整片审查**：`review_render.py` 按 edit_plan 用 ffmpeg 代理复现（竖屏=split+gblur sigma25 背景+scale=-2:1080 前景 overlay 模拟画布模糊；叠化除外=硬切；逐段 `-frames:v round(dur*30)` 防 fps 滤镜每段+2帧漂移）→ concat → numpy 精确摆旁白轨（块边界跳变>0.15 报爆音）→ amix normalize=0 → subtitles 烧字（**filter 里路径带盘符冒号会解析炸，改 cwd+相对文件名**）→ 接触表 fps=1 tile + 边界帧 select eq(n\,X) + 每 10s RMS/峰值 → 大模型 ASR 听 mix.wav 对照字幕查听感。
- ffmpeg 9 无 `-vsync`，用 `-fps_mode passthrough`；ffprobe 取旋转要 `-show_entries stream=width,height:stream_side_data=rotation`（`stream=side_data_list` 不返回），编码横+rotation90=竖屏显示，漏判会把脸拉扁。
- 审查实测问题类型（v2→v3 已修）：①A-roll 中段絮语 ASR 听不清→该段静音保画面；②同机位跳切（剪口误跳过 1s）→0.5s 叠化遮；③B-roll 画外音碎语与旁白重叠→结尾段静音；④电平不齐（旁白 RMS 0.04 vs 现场人声 0.11，差约 9dB）→旁白/宿舍 1.8、现场 0.8、环境 0.4，峰值 0.875→0.703；⑤旁白长段无字幕（开场 13s 空窗）→补字幕；⑥同镜头续接处加叠化=鬼影→去掉。
- 字幕重叠坑：pycapcut `Track.add_segment` 抛 `SegmentOverlap`（track.py:118）；相邻旁白块字幕时长不得超过块间隔+块长，合并短句为一条更稳。
- 代理不还原草稿的字幕位置/字号（libass 默认底部）与叠化→这两项仍须 CapCut 编辑器目视，别把代理现象当草稿缺陷。

## v4 补充（2026-11-22，原片升级 + 不依赖编辑器的成品导出）

- **剪映专业版/CapCut PC 转场语义：总时长不变**。切点居中 D/2 重叠：片段边缘外有余量(handle)就用余量，没有就「添加重复帧创建转场」冻结补（[vsx10.com/a/1396.html](http://www.vsx10.com/a/1396.html)）；移动端剪映才会吞时长（[知乎](https://www.zhihu.com/question/574909305)）。→ 草稿里按绝对时间摆旁白/字幕在 PC 版不会因转场错位；ffmpeg 复现时给每段补 D/2 头尾（handle 或 tpad clone），xfade offset=切点-D/2，总长不变。
- ffmpeg xfade 混链坑：concat 输出 timebase 1/1000000 与 mp4 解复用 1/15360 不一致报 `First input link main timebase (1/1000000) do not match ... xfade timebase (1/15360)` → 每个输入与每级输出都 `settb=AVTB` 归一。
- 换音轨源对齐：同一次录音的压缩版与原版用时移 δ 对齐——两版各跑 silencedetect，静音锚点差值取中位数（本例 27 锚点 δ=-0.0427s），chunks 整体平移即可，不必重跑 ASR。
- 过曝源素材调色副本：`eq=contrast=1.08:saturation=1.15:brightness=-0.03` + crf18 重编码，草稿改指副本；原件不动、可回滚。
- CapCut 删草稿进 `草稿根\.recycle_bin\<名>`（含 (1)/(2) 副本），可恢复；发现草稿「消失」先查回收站再下结论。
- GUI 第 4 种开草稿法也失败：首页键盘 TAB+ENTER 开出 0,0 全屏**卡死白窗**（PrintWindow 与真实截屏均纯白，40s 无内容）→ WM_CLOSE 关掉恢复首页。结论不变：首页开草稿只能真实鼠标。
- 混音电平：先按源 RMS/峰值配平各轨音量（本例旁白 1.2/现场 0.6/宿舍 0.95/环境 0.4/BGM 0.16），混音峰 >0.98 才触发全局安全衰减（本例 1.079→-0.8dB）；别靠全局衰减救削顶（会把安静段一起压掉）。成品 QA 双保险：关键时间点抽帧目视 + 大模型 ASR 回听混音对照字幕表。
- v5 听感三条：①「静音保画面」会翻车——用户听感优先人声连续，宁可保留听不清的絮语；恢复时与相邻同源段同电平才无缝，且先测源段峰值定电平（中段峰 0.886，×1.8 直接削顶）。②硬切点加纯音频淡入淡出（plan 键 afade_in/afade_out，与视频 fade 分离）；线性交叉淡化宽度 ≤0.4s，0.8+0.8 会在切点留近静音洞。③草稿被 CapCut 打开时 .locked 占用，create_draft(allow_replace=True) 的 rmtree 报 PermissionError WinError32 → 另建新草稿名，不动用户会话。
- v6 语气完整性三条（用户 m01335：「时间不重要，重要的是平淡」；上调语气被截=「抽象」）：①切点必须落在 silencedetect 实测静音锚点内（句尾落下后 ≥0.25s 才切、下句起调前 ≥0.25s 进），上调语气一律让它说完；连续独白宁可整段不内切。②停顿两侧的切点**不要**加音频淡化——淡化截语气反而突兀；afade 只用于环境声床的接落。③export 缓存纪律：时间线/段长变更后 fin_seg*.mp4 与 final_video.mp4 全部失效（段索引会移位），必须清缓存重编码，否则 mux 出旧画面+新音频的错位成品；**只改字幕**时仅 final_video.mp4 失效（fin_seg 与字幕无关可复用）。
- v7 字幕校对法（用户 m01385「字幕识别准确一点」）：①vosk 大模型仍不够准 → faster-whisper 1.2.1 + large-v3（hf-mirror.com/Systran/faster-whisper-large-v3，model.bin 3.09GB，curl -sL 五文件）词级转写，口语干净一个量级；pip 走阿里云镜像装进 pylibs。②av 19 与 faster-whisper decode_audio 不兼容（TypeError: open() got an unexpected keyword argument 'metadata_errors'）→ ffmpeg -f f32le -ac 1 -ar 16000 解出 numpy 数组直接喂 transcribe。③**幻影字幕坑**：被 chunks 剪掉的句子若留着字幕=画面无声处挂字，逐句核对「字幕文本∈该块音频词序列」才能发现；字幕起止一律用词边界（首词 start/尾词 end），同轨留 ≥0.04s 间隙防 SegmentOverlap。④同音误字按语义+用户自述定（做→坐）；两模型分歧处取语义通顺者。
- 收尾归档纪律（用户 m01552/m01560，详见 [[规则-工作区不留视频-交付即清中间产物]]）：①工作区不留视频——export/review 脚本的成品与缓存落 D:\AI-Tool-State\<任务>\输出 与 *-cache，工作区证据只留 jpg/ass/srt；交付确认后清成品+缓存（本轮清 ≈2.0GB）。②**草稿依赖媒体不可清**：CapCut 草稿引用 origins 备份/graded/bgm/narr_orig.m4a，草稿未删前清它们=丢媒体。③审查脚本的旁白源要跟 plan 同步换（曾潜 bug：plan 换 narr_orig.m4a 后 review_render 仍读旧 wechat_narr.wav）；m4a 用 ffmpeg 解 f32le 喂 numpy，wave 读不了。④用户剪辑偏好成文：全局记忆 feedback-vlog-plain-edit-preferences.md（平淡唯一目标、切点进静音锚点、上调语气说完、字幕逐字原话）。

## v8 补充（2026-11-24，既有草稿「网店商品短视频」文件级细节优化）

- **优化用户既有草稿走文件级，不碰 GUI**：备份整草稿目录 → 确认 CapCut 进程退出、`.locked` 消失 → 改 `Timelines/<uuid>/draft_content.json` 真身与根 `draft_content.json` 兼容副本（改后保持两份一致，可直接 Copy）→ 同步 `draft_meta_info.json` 与 `root_meta_info.json` 的 `all_draft_store[].tm_duration` → 重开 CapCut，**首页卡片时长显示随之更新**（本例 00:55→00:50），可作「CapCut 认可改后草稿」的间接验证；进编辑器仍须真实鼠标双击（再次复核）。
- 结构对齐清单（本例缺陷与修法；脚本 `D:\AI-Tool-State\capcut-opt\optimize_draft.py`，前置断言不符即中止；备份 `D:\AI-Tool-State\capcut-opt\backup-1124`）：①滤镜/调整段边界须对齐主轨切点，否则镜头中途跳色（延长现有段补空窗，沿用用户原参数、不新造调色）；②主轨终点 < 总时长 = 黑尾，duration/BGM/节拍标记同步裁；③分屏溢出、四宫格 transform 亚像素错位 → 吸附精确 ±0.5；④speed 浮点噪声 round(2) 清理；⑤BGM 新建 audio_fade 材料挂 segment 的 extra_material_refs（fade_in_duration=500000 / fade_out_duration=1500000，µs）。
- **首页单击+Enter 同样触发白窗僵尸**（复现 v4 的 TAB+ENTER）：Enter 打到隐藏「版本更新」弹层，全部窗口 IsWindowVisible=0 但进程活着，恢复出的窗口纯白。恢复法：`Stop-Process -Name CapCut -Force` + 重开（`Start-Process 'D:\CapCut\CapCut.exe' -WorkingDirectory 'D:\CapCut'`）；强杀后必须重读草稿确认未被僵尸实例内存反写（本例安全）。安装路径 `D:\CapCut\CapCut.exe`（开始菜单快捷方式解出）。
- 只对齐结构、不改用户调色值与文字内容；内容级增补默认留选项给用户，用户授权「自己看最优解」时再代决。
- 片尾卡最优解（2026-11-24 用户 m00233 授权代决）：原草稿 5.1s 黑尾实为预留片尾位 → Pillow 生成 1920×1080 品牌卡 PNG（复用开场两套字体 ttf、暖白渐变+粉晕、品牌+品名+slogan），**烘字 PNG 可 read_image 自验观感**，比 CapCut 文本材料风险低（代价：文字不可在 CapCut 编辑）。接入：克隆草稿既有 photo 材料（背景.jpg）改 path/宽高；克隆 photo 段只留 canvas+speed(1.0) 引用、去逐片段调色；主轨追加 3s；BGM 延至新结尾使淡出自然落位；duration/meta/root_meta 同步（52.45s，首页卡 00:53 间接验证）。备份 `D:\AI-Tool-State\capcut-opt\backup-before-endcard`。转场仍不加：快切是广告节奏，且 transitions schema 未经编辑器目视，风险>收益。
- **外部编辑前必须重读当前 JSON**：用户会在编辑器里自己改参数并自动保存（本例用户已把冷白 0.5975→0.4），拿旧快照当基线会断言失败或覆盖用户改动。
- 局部「白得夸张」修法（2026-11-24 用户 m00279 圈四宫格）：叠层归因=冷白+自然+调整3 亮度高三层叠在最亮源上 → 自然 0.8→0.45 + 四宫格逐片段 brightness-0.15/highlight-0.25 回拉（克隆既有 effect 材料改 value，adjust_params 为空、值只存 value，克隆安全）；只动目标场景、其余全片保持。备份 `D:\AI-Tool-State\capcut-opt\backup-before-natural`。

## 关联

- [[经验-无字幕视频批量ASR-whisper装不上改vosk小模型加imageio-ffmpeg]]（vosk 路线的前置经验）
- [[经验-微信msg-video临时文件会被自动清理-收到媒体立即备份]]（本轮旁白源视频中途消失的教训）
- 任务档案：`G:\AIrenwu\01_任务归档\2026-11-20_平静vlog剪辑\`（拍摄方案、准备报告、探针与 ASR 脚本、自测证据）
