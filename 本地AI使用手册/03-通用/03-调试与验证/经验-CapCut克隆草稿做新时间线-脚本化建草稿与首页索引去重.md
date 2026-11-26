# 经验-CapCut 克隆草稿做新时间线-脚本化建草稿与首页索引去重

- 状态：verified
- 日期：2026-11-24
- 场景：用脚本（Python + json）给 CapCut 国际版 9.8.0.4213 生成一份全新草稿（自定义分镜/滤镜/BGM/PNG 文案层），并保证在 CapCut 里能正常打开、预览、保存。
- 关联：`经验-CapCut国际版草稿自动化-pycapcut建草稿与vosk离线字幕.md`

## 结论（可直接照抄的做法）

1. 不要去猜 `draft_content.json` 的最小合法结构。**克隆用户已有的一份能打开的草稿目录**（`shutil.copytree`），只重写 tracks/duration/材料引用，schema 天然合法。
2. 片段的"附加材料"（`extra_material_refs`，指向 speeds / canvases / material_colors / vocal_separations / sound_channel_mappings / hsl / effects / placeholder_infos / material_animations）**必须整组深拷贝并换新 id**，同时把新 id 登记进 `id→材料` 索引；只改 `material_id` 会留下悬空引用，CapCut 打开后片段可能变成静帧或直接丢轨。
3. 变速：改片段 `speed` 之外，还要改它引用的 `speeds` 材料的 `speed`（`mode=0`），两处不一致时时间线按源时长显示。
4. 图片当视频段用：克隆模板里 `photo` 材料的字典，改 `path/material_name/width/height/type="photo"`；片段本身以模板里的「图片段」为模板克隆（本项目用 endcard.png 段）。
5. **render_index 实测约定**：主轨 0；画中画/图片叠加轨 1（同轨多段会是 1、3…，但同轨都填 1 也能正常显示）；文字 14000；滤镜 10000 起、每条滤镜段唯一；音频 0。`track_render_index` = 该轨道在 `tracks` 数组里的下标。
6. 轨道字典只认 `id/type/flag/attribute/name/is_default_name` 这几个键；主轨 `attribute=1`、其它 0；画中画视频轨 `flag=2`，其余（text/filter/adjust/audio）`flag=0`。
7. **图片路径可以写绝对路径**（如 `D:/.../card01.png`），CapCut 会以「导入素材=保留在原有位置」方式引用；但注意**草稿从此依赖这些外部文件，不能当中间产物清理**。模板自带的 `##_draftpath_placeholder_<uuid>_##/endcard.png` 是运行时宏（按草稿目录解析），克隆时保持原样即可，不要替换成绝对路径。
8. 换 timeline uuid 要同时改：`draft_content.json`（根）、`Timelines/<uuid>/draft_content.json`（真身，且要与根**完全一致**）、`Timelines/project.json`、`timeline_layout.json`。`draft_meta_info.json` 要改 `draft_id/draft_name/draft_fold_path/tm_duration/draft_timeline_materials_size_`。`draft_content.json["id"]` 与 `draft_meta_info.json["draft_id"]` **本来就是两个不同 id**，不必强求相同（CapCut 保存时还会自己改写 draft_id）。
9. 首页列表由 `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\root_meta_info.json` 的 `all_draft_store` 决定：每条要写全 `draft_id/draft_name/draft_fold_path/draft_json_file/draft_cover/draft_timeline_materials_size`。**每次重建草稿都会产生新 draft_id，旧条目不会自动删，首页会出现同名重复卡片**——所以脚本里必须按 `draft_fold_path` 去重（而不是按 draft_id），并顺手删掉目录已不存在的条目。
10. `draft_timeline_materials_size` 填 0 会让首页显示「0.0B」，观感很差；遍历 materials 的 `path` 累加 `os.path.getsize`（跳过 `##` 宏路径）即可回填真实体积。
11. 想换首页封面：直接把成片某一帧写成草稿目录里的 `draft_cover.jpg`（1920x1080 即可），CapCut 首页立刻生效。

## 验证方法（不依赖 GUI 也能先自证）

- 脚本内断言：主轨首尾相接、累计时长 == 目标时长。
- 落盘后跑一遍静态校验：两处 `draft_content.json` 相等；遍历所有片段的 `material_id` 与 `extra_material_refs` 均能在 materials 里找到（悬空 0）；所有 `path` 存在（只允许 `##` 宏路径缺失）；轨道类型与段数符合预期。
- 最后一定要**真开一次**：`Start-Process D:\CapCut\CapCut.exe` → 首页点卡片。CapCut 正常打开后会**把草稿重新存盘**（`draft_content.json`/`draft_meta_info.json`/`draft_cover.jpg` 的 mtime 会更新）——mtime 变化 + 时间线/预览正常，就是"结构被官方引擎认可"的硬证据；重存后再校验一次，确认结构与时长没被改坏。

## 踩过的坑

- **PowerShell 里用 `python -c` 拼 Windows 路径会翻车**：`G:\AIrenwu\10_视频广告\...` 里的 `\10` 被当成 `\x08`，报 `OSError: [Errno 22] Invalid argument`。改文件一律用编辑工具，别用命令行拼路径。
- **CapCut 抢占前台**：每次工具调用返回后前台会回到编辑器/浏览器，`SetCursorPos + mouse_event` 会打到错误窗口。可靠写法是**一个 pwsh 脚本里完成**：`Win+D → ShowWindow(SW_RESTORE)+SetForegroundWindow(CapCut) → SetCursorPos → 点击 → 截图`。
- **截图像素坐标要换算**：屏幕 2048x1280，而预览图常被降采样到 1600x1000，按预览坐标直接点会整体偏移约 1.28 倍，点空。
- **关不掉 CapCut**：`WM_CLOSE` / `Alt+F4` 对它无效（无边框窗口 + 编辑器自己拦截）。可行的是**对每个可见顶层窗口都发一次 `WM_CLOSE`**（先用 `EnumWindows` 拿到该进程的多个窗口句柄），主窗口会立即关闭，剩下 6 个后台服务进程常驻属正常。抢不到前台时 `Alt+F4` 会打到别的窗口，别乱用。
- 克隆草稿前确认 CapCut 没在跑（检查是否有 `.locked`）；写完别再用同一个 draft_id 反复追加索引条目。

## 适用范围与剩余风险

- 适用于 CapCut 国际版 9.8.x（177.0.0 / version=360000 系草稿）。国内剪映专业版字段名与加密策略不同，不可直接套用。
- 未验证：转场、关键帧动画、贴纸、文字材料（`content.text`）的脚本化生成——这些字段没做过目视验证，不上线。
- 剩余风险：克隆草稿会带进模板里的历史材料（本次克隆后 materials 仍有模板遗留的 text/sticker 等未被引用条目，CapCut 正常忽略，体积略大）。
