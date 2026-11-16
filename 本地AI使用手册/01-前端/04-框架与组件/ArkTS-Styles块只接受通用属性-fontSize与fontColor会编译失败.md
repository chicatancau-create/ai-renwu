---
title: "ArkTS @Styles 只接受通用属性：fontSize/fontColor 会编译失败"
date: 2026-11-15
domain: frontend
category: 04-框架与组件
status: verified
severity: medium
stack: [HarmonyOS, ArkTS, ArkUI, DevEco Studio]
tags: [@Styles, 样式复用, CommonAttribute, 编译错误, fontSize, fontColor]
---

# 问题：@Styles 里写 fontSize/fontColor 直接编译失败

## 一句话结论

`@Styles` 代码块内的接收者类型是 `CommonAttribute`，只接受**通用属性**；`fontSize()`、`fontColor()` 这类组件专有属性会报 `10505001 ArkTS Compiler Error: Property 'fontSize' does not exist on type 'CommonAttribute'`，块里有几处就报几条，且整模块编译中止。

## 触发条件与影响

- 项目或功能：把输入框/按钮的样式抽成 `@Styles` 复用（课件 7.4 步骤4 的写法）
- 环境与版本：HarmonyOS `compatibleSdkVersion 6.1.1(24)`，DevEco 自带 node + hvigor 命令行构建
- 触发条件：`@Styles` 块内出现 `.fontSize(...)` 或 `.fontColor(...)`
- 影响范围：`CompileArkTS` 阶段失败，不是警告；一处页面写了就整模块挂

## 复现步骤

1. 前置条件：任一 `@Component` / `@ComponentV2` 页面
2. 操作或命令：写一个把文字属性也塞进去的样式块

```ets
@Styles
inputStyle() {
  .height(48)
  .fontSize(14)            // ← 触发
  .fontColor('#1A1A1A')    // ← 触发
  .backgroundColor('#F2F3F5')
  .borderRadius(14)
}
```

3. 预期结果：样式复用生效，编译通过
4. 实际结果：每个专有属性各报一条 `10505001`，`COMPILE RESULT:FAIL`

## 证据

```
1 ERROR: 10505001 ArkTS Compiler Error
Error Message: Property 'fontSize' does not exist on type "CommonAttribute". At File: .../pages/me/Login.ets:38:6
2 ERROR: 10505001 ArkTS Compiler Error
Error Message: Property 'fontSize' does not exist on type "CommonAttribute". At File: .../pages/me/Login.ets:59:6
...（Reg.ets / LoginApi.ets / Edit.ets 同形，共 8 条 fontSize）
COMPILE RESULT:FAIL {ERROR:9 WARN:17}
```

把 `fontSize` 移走后，同一批位置又报出 `Property 'fontColor' does not exist on type "CommonAttribute"`，证明是类型限制而不是笔误。

## 根因分析

- 已确认的根因：`@Styles` 的 eDSL 接收者是 `CommonAttribute`；`fontSize`/`fontColor`/`placeholderColor` 属于 `TextAttribute`、`ButtonAttribute`、`TextInputAttribute` 等专有接口，不在 `CommonAttribute` 上。
- 排除过的假设：不是 SDK 版本问题——同一 SDK 下 `.height`、`.borderRadius`、`.border({width,color})`、`.backgroundColor`、`.stateStyles({...})`、`.linearGradient({...})`、`.shadow({...})` 在 `@Styles` 内都能编过。
- 问题归属：本次修改引入。

## 最小修复

`@Styles` 只留通用属性，文字语义的属性回到调用点：

```ets
@Styles
inputStyle() {
  .height(48)
  .backgroundColor(INPUT_BG)
  .borderRadius(CHIP_RADIUS)
  .border({ width: 1, color: BORDER_LIGHT })
}

TextInput({ placeholder: '邮箱', text: this.email })
  .fontSize(14)
  .fontColor(TEXT_MAIN)
  .inputStyle()
```

代价是每个调用点多两行；换来的是编译可过、且 `@Styles` 仍可被输入框与按钮共用。

## 验证记录

- [x] 编译：`hvigorw.js clean --no-daemon` + `assembleHap --no-daemon` → BUILD SUCCESSFUL，33 任务里 32 执行、ERROR 0
- [x] 静态检查：自写脚本统计「import 了但正文未用的具名」= 0
- [x] 构建产物核对：hap 内 11 条路由、1 条 routerMap、18 个 rawfile 与改动前一致
- [ ] 运行时目视：本机模拟器无系统镜像，未做

## 可复用规则

抽 `@Styles` 前先按通用属性白名单筛一遍：`width / height / size / padding / margin / border / borderRadius / backgroundColor / opacity / visibility / position / stateStyles / linearGradient / shadow`。凡带文字语义的（`fontSize`、`fontColor`、`fontWeight`、`lineHeight`、`textAlign`、`maxLines`、`textOverflow`、`placeholderColor`）一律留在组件调用点上。要用专有属性做复用时改用 `@Extend(Text)`，但那是另一种写法，别和 `@Styles` 混在一处。

## 适用范围与不适用范围

- 适用：ArkTS 状态管理 V1 与 V2 的 `@Styles`
- 不适用：Web CSS/SCSS 类复用；`@Extend` 的专有属性场景

## 剩余风险

`@Styles` 内写 `.stateStyles({...})`、`.linearGradient({...})` 只证明**写法合法**；编译产物 `ets/modules.abc` 里查不到这两个符号（被编译期内联），所以运行时是否真生效仍未证实。

## 关联

- 相关记录：[[01-前端/04-框架与组件/ArkUI-链式调用挂错节点+空容器无尺寸导致背景色不显示]]
- 相关分类：[[01-前端/前端索引]]
- 相关代码、命令或文档：`D:/DevEco Studio/tools/node/node.exe D:/DevEco Studio/tools/hvigor/bin/hvigorw.js assembleHap --no-daemon`；本次改动落在课件商城工程 `entry/src/main/ets/pages/me/*.ets`（该工程目录后续被并入 `Harmony/ShoppingMallApp-ai`）
