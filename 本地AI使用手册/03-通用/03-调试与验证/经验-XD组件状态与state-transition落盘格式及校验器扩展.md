---
title: "XD 组件状态（Component States）与 state-transition 落盘格式，及四道校验器的状态盲区扩展"
date: 2026-11-24
domain: common
category: 03-调试与验证
status: verified
severity: medium
stack: [Adobe XD, .xd, ZIP, JSON, Python]
tags: [XD, 组件状态, syncRef, state-transition, 逆向, 校验器]
---

# 问题：XD「点击切换组件状态」如何落盘，以及校验器为何对纯状态文件误报 FAIL

> `verified`：格式由可用样本逐字段逆向，克隆产物通过四道校验 + 深度结构自检；GUI 点击回归未做（见剩余风险）。

## 一句话结论

XD 组件的「默认状态 = 母版 group.children、非默认状态 = meta.ux.states[]、实例 = syncRef 树 + syncMap」，
点击切换靠 `state-transition` 交互的**双重表示**（节点 meta.ux.interactions + interactions/interactions.json）；
原有 `validate_proto.py` / `inter_probe.py` 不认 state-transition 与母版/状态组 id，会对**本来就正确**的纯状态文件误报 FAIL，需扩展。

## 触发条件与影响

- 项目或功能：`E:\XD\组件初始状态2(成品).xd`（101 symbols，含 UI kit「Credit Cards」6 状态、「组件 102」3 状态）。
- 环境与版本：Adobe XD 58；.xd = ZIP，改成员 JSON；Python 读样本（PS 5.1 按 GBK 解码会坏中文）。
- 触发条件：要把 Cards 页散卡做成「点击切换 + 组件状态」，像左页 Spending；并跑四道校验。
- 影响范围：任何含组件状态/纯 state-transition 的 .xd；校验器盲区会让正确文件被判 FAIL。

## 复现步骤

1. 前置：打开成品 .xd，跑 `validate_proto.py` / `inter_probe.py`。
2. 操作：观察 FAIL。
3. 预期：正确文件应 PASS。
4. 实际：validate_proto 把 state-transition 判 unknown action；inter_probe 把母版组 id/状态组 id 当实例内部键判 FAIL，且纯状态文件无画板导航被判「画板不可达」。

## 证据

- 原始成品交互 245 规则/240 键，100% state-transition，homeArtboard=None。
- inter_probe 误报：71 键是母版组 id（sym.id，整组件点击）、46 键是状态组 id（st.id，如 Radio Button「Off」e2f868ad、Toggle Switch「Off」27a85c29）——原只 walk 状态子节点漏 st 本身。
- 扩展后对**未改动原始成品**也 PASS（validate_proto 253/0、inter_probe 0 fail）→ 证明非为自产文件量身放宽。

## 根因分析

- 已确认根因：校验器建模早于组件状态功能（SCHEMA.md §6.4/§14.11 明言 syncRef/实例「未建模」）。
- 问题归属：修改前已有（校验器盲区），非本次产物引入。

## 最小修复

格式要点（详见 `C:\Users\Admin\.dsh\tools\xd\SCHEMA.md` §16，本次新增）：
- 母版 `meta.ux`：symbolId、stateId（默认 stateId==symbolId≠母版 id）、states[]、width/height、canonicalPaddingTop/Bottom。
- 状态项：`{type:"group",name,id,meta.ux:{symbolId,syncMap:{默认节点id:本态节点id},stateId:<自身id>,symbolPaddingTop/Bottom},group.children}`。
- 实例：`meta.ux:{nameL10N:"SHAPE_COMPONENT",symbolId,isMaster:true,syncMap:{当前态母版节点id:实例guid},stateId,localTransform}`，子 `syncRef:{syncSourceGuid:<母版节点id>,guid}` 镜像母版树；顶层 transform.tx=画板x+localTransform.tx。
- 交互双重表示：节点 guid==json id；data.interaction==json 条目去 id；destination 须∈源节点所属 symbol 的状态 id。
- 克隆 technique：深拷贝 kit 母版→全量改 id（母版/symbolId/状态/节点/syncMap 键值/destination/guid）→加进 symbols→建实例替换散件→interactions.json 追加新键。本次 remap 37 id、交互 240→250。

校验器扩展（已落地于工具）：
- `validate_proto.py`：homeArtboard 可选；收集 sym.id+状态节点；新增 state-transition 分支（dest 须∈本源 symbol 状态 id）。
- `inter_probe.py`：master_ids 加 sym.id+st.id+状态子节点；可达性由「有画板导航或 previous-artboard」门控，纯状态文件跳过该 FAIL 记 note。

## 验证记录

- [x] 静态/结构：四道校验对新文件全 PASS（validate 20/0、validate_proto 263/0、geom_check 0 fail、inter_probe 0 fail）。
- [x] 深度自检：6 状态 syncMap 键==默认卡/值==本态卡、symbolId/stateId 正确、10 内嵌交互与 json 一致且 dest 合法、实例 syncMap/syncRef 一致、散卡已删 → ALL CONSISTENT。
- [x] 完整性：zip testzip None、102 symbols、原 Credit Cards 完好、全 JSON 可解析、mimetype 首 STORED。
- [ ] GUI 点击回归：未做（不抢用户前台 + 用户活 XD 有未保存改动）。

## 可复用规则

- 改 XD 组件状态/交互时，节点 meta.ux.interactions 与 interactions.json **必须同步改**，guid 一致、destination 指向本源 symbol 的合法状态 id。
- 交付「自有命名组件 + 状态」用克隆 kit 母版 + 全量改 id，而非直接实例化 kit（用户要「增加状态」时）。
- 校验器对纯状态文件 FAIL 先怀疑盲区（sym.id/st.id 未收集、无画板导航），用未改动原始样本复核扩展是否通用，再下结论。
- 适用：含组件状态的 .xd。例外：跨 symbol 的 state-transition 仍应 FAIL（destination 不属本源 symbol）。

## 适用范围与不适用范围

- 适用：XD 58 组件状态逆向/生成/校验；UI kit 母版克隆。
- 不适用：XD 真机点击行为的最终确认（需用户预览）；gradient/compound 等仍未建模节点。

## 剩余风险

- GUI 点击切换未真机回归；结构上与**可用的** Credit Cards 逐字段同构（仅改 id），预期一致，最终由用户打开 `E:\XD\组件初始状态2(成品)_卡片切换.xd` 预览确认。
- 用户活 XD 有未保存的「组件 103」，与新交付文件同名组件可能冲突；建议打开新文件、原会话改动可不保存。

## 关联

- 相关记录：[[03-通用/03-调试与验证/经验-XD拖移auto-animate落盘格式用亲笔样本定案与校验器盲区|XD 拖移 auto-animate 落盘格式与校验器盲区]]
- 相关代码/文档：`C:\Users\Admin\.dsh\tools\xd\SCHEMA.md` §16；`validate_proto.py`、`inter_probe.py`；交付 `E:\XD\组件初始状态2(成品)_卡片切换.xd`；备份 `E:\XD\备份\组件初始状态2(成品)_原始备份.xd`。