---
title: "XD 拖移 auto-animate 落盘格式用亲笔样本定案与校验器盲区"
date: 2026-11-24
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Adobe XD 58 UWP, Python]
tags: [XD, 交互原型, 私有格式, 校验器, 证据]
---

# 问题：XD 拖移交互落盘格式无本地先例，校验器对新 action 与 symbol 键误报 FAIL

> 2026-11-16 实测并交付，2026-11-24 归档前复核回写。

## 一句话结论

私有格式无先例时别拿插件 API 文档猜落盘串——用软件自己的「亲笔」样本定案：XD 拖移 = `triggerEvent:"drag"` + `action:"auto-animate"`（auto-animate 是独立 action，不是 transition 枚举值）；校验器报 FAIL 先跑未改动的基线区分「校验器盲区」与「文件真坏」，修盲区必须配负例证明没放水。

## 触发条件与影响

- 项目或功能：xd-authoring 工具链（`C:\Users\Admin\.dsh\tools\xd\`）给老师轮播底稿加「鼠标拖移跳转」。
- 环境与版本：Adobe XD 58.0.12.9（UWP 包 `Adobe.XD_pc75e8sa7ep4e`）；interactions.version=0.24。
- 触发条件：本地 7 个 .xd 全无 drag 样本；UXP 插件 API 文档的 transition 枚举（autoAnimate/dissolve/push/slide/none + fromSide）是 API 表示，不是落盘串。
- 影响范围：`validate_proto.py` 对正确文件误报 12 条 FAIL（6×`unknown action 'auto-animate'` + 6×symbol 键 `matches NO node or artboard`），差点把合格交付物判死。

## 复现步骤

1. 前置条件：任一含 symbol 实例交互的 .xd（如轮播底稿）。
2. 操作或命令：`python validate_proto.py <未改动的原件>`。
3. 预期结果：原件是 XD 自己存的，应当 PASS。
4. 实际结果：原件也 FAIL 7（6 个 symbol 键 + homeArtboard None）⇒ 是校验器盲区，不是文件问题。

## 证据

- XD 活缓存亲笔条目（float32 痕迹 `0.800000011920929` 证非手写）：`C:\Users\Admin\AppData\Local\Packages\Adobe.XD_pc75e8sa7ep4e\LocalState\a6de0165af37885d38b3ee2ef6fe2733\interactions.json`，tap+auto-animate 条目 `{"properties":{"transition":"dissolve","duration":0.800000011920929,"easing":"ease-out",...},"triggerEvent":"tap","action":"auto-animate",...}` → 落盘副本 `C:\Users\Admin\.dsh\tools\xd\provenance\drag_format_evidence.json`。
- 用户自己在 XD 里做的 drag 版本（`E:\XD\拖动图.xd`，2026-11-16 17:09）抽出的 interactions：`triggerEvent:"drag"` + `action:"auto-animate"`，`duration:0.30000001192092896`、`easing:"linear"`（XD 拖移缺省）→ 副本 `C:\Users\Admin\.dsh\tools\xd\provenance\drag_format_evidence_user.json`。与工具产出逐字段同构，双向证实。
- 交付物 `E:\XD\自动播放轮播图（拖移跳转版）.xd`（SHA256 `9200ba7a335ebbd1a9c06c01b10347d50ed9c95b8b803640323c4c4360e217a7`）：17 条 = 原 11（2 time + 9 tap）+ 新 6 drag。
- 负例：把一条 drag 的 destination 改成 `deadbeef-0000-0000-0000-000000000000` → validate_proto 精确 FAIL 该条 ⇒ 修复没放水。

## 根因分析

- 已确认的根因：①插件 API 表示 ≠ 落盘串（autoAnimate 枚举在落盘里是独立 action `auto-animate`，`properties.transition` 残留 `dissolve` 被忽略）；②validate_proto 的 action 白名单没有 auto-animate，节点采集没覆盖 symbol 母版/实例键（母版在 `resources/graphics/graphicContent.agc` 的 `resources.meta.ux.symbols[].group.children`，实例副本 id 要靠 `meta.ux.syncMap` master→inst 映射并入）。
- 排除过的假设：「文件写坏了」——未改动基线同样 FAIL，排除；「drag 要配 slide-left 之类 transition 串」——UXP 文档明确 drag 只能配 autoAnimate 的 goToArtboard，且两份亲笔样本都是 auto-animate。
- 问题归属：修改前已有（校验器盲区）+ 格式知识缺失。

## 最小修复

- `xdpatch.py` make_entry：link 带 `"autoAnimate": true` → `action:'auto-animate'`（transition 仍写 dissolve 残留，与 XD 亲笔一致）。
- `validate_proto.py`：认 auto-animate（destination 必须是真实画板否则 FAIL）；采集 syncMap 与 symbol 母版/实例 id，where='symbol'。
- `SCHEMA.md` §10 补格式与证据指针；spec 留档 `C:\Users\Admin\.dsh\tools\xd\specs\自动播放轮播图拖移.json`。

## 验证记录

- [x] 格式化或静态检查：四校验全 PASS（validate.py 20/0、validate_proto.py 25/0、geom_check.py 0 fail/7 warn 皆底稿原有、inter_probe.py 0 fail/4 warn 皆底稿原有）（2026-11-16）。
- [x] 单元、集成或端到端测试：原生 xdpatch 从剥离副本复现交付物逐键全等（uuid 除外）；旧 spec 回归 7 tap/artboard-transition + 4 tap/previous-artboard 不变（2026-11-24 复核仍通过）。
- [x] 启动或手动回归：2026-11-24 复核 validate_proto 仍 25/0 PASS、交付物 SHA256 未变。
- [ ] 真机预览拖移手势：未跑（当时用户活跃使用 XD，按技能约束不抢前台）；格式已由用户亲笔 drag 样本双向证实。

## 可复用规则

1. 私有软件落盘格式无本地先例时，先找它自己的亲笔样本：活缓存（XD 在 `%LOCALAPPDATA%\Packages\Adobe.XD_pc75e8sa7ep4e\LocalState\<文档hash>\interactions.json`）或用户刚在软件里另存的文件；float32 痕迹（如 `0.30000001192092896`）可证条目是软件写的不是手拼的。
2. 插件 API/SDK 文档的枚举名 ≠ 落盘字符串，只能当线索不能当依据。
3. 校验器对新文件报 FAIL，先对未改动基线跑一遍：基线也 FAIL = 校验器盲区；修盲区后必须造负例（改坏一个字段应精确 FAIL）证明没放水。

## 适用范围与不适用范围

- 适用：XD .xd interactions 改造与校验；方法论适用于其他私有格式的逆向定案。
- 不适用：drag+其他 transition 组合（无真样本，只证实了 auto-animate）；别把本记录的 action 串推广到未经样本证实的其他触发器。

## 剩余风险

真机预览拖移手势未实测（格式双向证实但手势体验未验）；XD 升级后落盘格式可能变化，届时重新取亲笔样本。

## 关联

- 相关记录：[[踩坑-沙箱只放行工作区致写E盘被拒且write会抹掉源码BOM]]（同会话写 E 盘摩擦的另一面）
- 相关分类：03-通用/03-调试与验证
- 相关代码、命令或文档：`C:\Users\Admin\.dsh\tools\xd\SCHEMA.md` §10、`D:\Skills\xd-authoring\SKILL.md`、`C:\Users\Admin\.dsh\tools\xd\specs\自动播放轮播图拖移.json`、`C:\Users\Admin\.dsh\tools\xd\provenance\drag_format_evidence.json` 与 `drag_format_evidence_user.json`、交付物 `E:\XD\自动播放轮播图（拖移跳转版）.xd`、交付说明 `E:\XD\交付说明.md`