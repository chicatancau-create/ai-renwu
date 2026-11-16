---
title: "uni-app 列表页白屏：data 双层嵌套致 list 不存在，v-for 遍历 undefined"
date: 2026-11-15
domain: frontend
category: 04-框架与组件
status: verified
severity: high
stack: [uni-app, Vue, HBuilderX, uni-ui]
tags: [白屏, data, v-for, 响应式数据, key, uni-list, 静态资源路径]
---

# 问题：uni-app 列表页白屏，data 双层嵌套致 list 不存在

## 一句话结论

`data()` 内部又写了一层 `data()`，组件实例上只有 `data` 方法、没有 `list` 数据，模板 `v-for="item in list"` 遍历 `undefined` 导致渲染中断，页面白屏并长期停在"读取中"；同时 `:key="id"` 应为 `:key="item.id"`。

## 触发条件与影响

- 项目或功能：uni-app 项目 wofule 的 `pages/foodlist/foodlist` 菜品列表页（tabBar 页面）
- 环境与版本：HBuilderX 5.33，uni-ui（uni-list 已通过 uni_modules 安装，easycom 自动引入）
- 触发条件：页面加载即触发，模板渲染时读取不到 `list`
- 影响范围：整个列表页空白，四条菜品数据均不渲染；无编译错误提示，属于静默失效，容易误判为浏览器或 dev-server 问题

## 复现步骤

1. 前置条件：页面组件写成双层 `data()` 结构（见根因代码）
2. 操作或命令：HBuilderX 运行到内置浏览器，访问 `/pages/foodlist/foodlist`
3. 预期结果：`uni-list` 渲染出烤鸭、回锅肉、茄子、宫保鸡丁四条
4. 实际结果：WebView 一直显示"读取中"，模拟器中该页面纯白，仅标题栏"同学"和 tabBar 正常

## 证据

```javascript
// 修复前结构（节选自实际文件）
export default {
  data() {
    return {
      data() {            // ← 多嵌套的一层
        return {
          list: [ {id:1,...}, {id:2,...}, {id:3,...}, {id:4,...} ]
        }
      }
    }
  }
}
```

Node 静态验证（vm 执行 SFC 的 script，实际执行结果）：

```
旧结构 this.list === undefined          # 根因复现
修复后 data 类型: function
list 是否存在: true
list 条数: 4
id=1 name=烤鸭 ... thumb=/static/images/1.png 图片存在=false
id=2 name=回锅肉 ... 图片存在=false
id=3 name=茄子 ... 图片存在=false
id=4 name=宫保鸡丁 ... 图片存在=false
```

模板第 6 行原写法 `:key="id"`，`v-for` 作用域内不存在独立变量 `id`，HBuilderX 该行有语法告警标记。

## 根因分析

- 已确认的根因：
  1. **双层 data 嵌套**：Vue 只调用组件选项最外层的 `data()` 并把其返回对象作为实例状态。外层返回的是 `{ data() {...} }`，实例上存在 `this.data`（一个函数），但不存在 `this.list`，内层 `data()` 永远不会被框架调用。
  2. **v-for 遍历 undefined**：`v-for="item in list"` 中 `list` 为 `undefined`，渲染中断，页面空白。
  3. **key 引用错误**：`:key="id"` 应为 `:key="item.id"`，循环变量是 `item`，没有裸 `id`。
- 排除过的假设：uni-list 组件未安装（实际 uni_modules 中已存在，easycom 正常）；pages.json 未注册（实际已注册且 tabBar 配置正常）；dev-server 故障（换浏览器无效，根因在代码）。
- 问题归属：修改前已有，手写/复制数据时多包了一层 `data()`。

## 最小修复

```javascript
export default {
  data() {
    return {
      list: [
        { id: 1, name: "烤鸭", icon: "/images/1.png", /* ... */ },
        // 共 4 条，数据内容原样保留
      ]
    }
  },
  methods: {}
}
```

模板同步修改：`:key="id"` → `:key="item.id"`。不涉及接口、数据结构和配置变更，仅修正选项层级与 key 绑定；四条业务数据内容逐字保留。

## 验证记录

- [x] 静态检查：Node（v22）vm 执行修复后 script，`data()` 返回含 4 条记录的数组，字段完整
- [x] 根因复现：同环境模拟旧结构，`this.list === undefined`
- [ ] 类型检查或编译：未执行（HBuilderX 项目无 package.json，无独立 CLI 构建链）
- [ ] 启动或手动回归：未执行，需在 HBuilderX 重新运行到浏览器确认四条列表渲染
- [ ] 缩略图：未通过，`static/images/1.png~4.png` 实际不存在（见剩余风险）

## 可复用规则

uni-app/Vue 页面白屏且无编译报错时，按以下顺序排查：

1. **先查 data 层级**：确认组件只有一层 `data() { return {...} }`，模板用到的每个变量都在该返回对象上。判断方法：在脚本里模拟 `data()` 调用，检查返回对象是否含模板引用的字段。
2. **v-for 三件套**：遍历对象必须真实存在且为数组；`:key` 必须挂在循环项上（`item.id`），不能写裸字段；key 值需唯一稳定。
3. **静态资源路径核对**：`:thumb`、`:src` 拼出的最终路径要与 `static` 目录实际文件逐一核对，路径区分大小写；数据里写 `/images/x.png` 而模板拼 `/static` 前缀时，文件必须位于 `static/images/`。
4. 内置浏览器长期"读取中"不要先怀疑环境，先确认页面组件是否在渲染阶段抛错；可换 Chrome 预览或用 Node 独立验证 script 部分。

## 适用范围与不适用范围

- 适用：Vue 2/3 与 uni-app（含 HBuilderX 可视化项目）的选项式 API 数据定义、v-for 渲染、静态资源路径排查
- 不适用：组合式 API（`setup`/`ref`/`reactive`）中数据未定义的场景，排查对象不同；原生小程序 `setData` 问题不适用

## 剩余风险

1. 运行时渲染回归未实际执行，需在 HBuilderX 重新运行确认；在当前已执行的静态验证范围内，未发现其他已知阻断问题。
2. `static/images/` 目录及 `1.png~4.png` 四张菜品图缺失，修复后列表文字可显示但缩略图加载失败。需在 `static` 下新建 `images` 文件夹并放入四张同名图片。

## 关联

- 相关记录：[[01-前端/04-框架与组件/ArkUI-链式调用挂错节点+空容器无尺寸导致背景色不显示]]（同为无报错的静默失效，根因均在结构层级）
- 相关分类：03-通用/03-调试与验证（无报错白屏的排查思路）
- 相关代码：`E:\fullstack-code\跨平台应用开发\wofule\pages\foodlist\foodlist.vue`
