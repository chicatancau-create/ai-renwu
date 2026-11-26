---
title: "CDP 给 uni-app H5 chooseImage 注入图片：DOM.setFileInputFiles 只触发 change 不走上传，必须 Page.setInterceptFileChooserDialog + backendNodeId 拦真实选择器"
date: 2026-11-25
domain: common
category: 03-通用/03-调试与验证
status: verified
severity: medium
stack: [Chrome DevTools Protocol, uni-app Vue2 H5, webpack-dev-server HMR]
tags: [CDP, setFileInputFiles, chooseImage, 文件选择器, 取证, HMR]
---

# 问题：headless 取证 uni.uploadFile 链路时，注入文件后零上传请求

## 触发条件与影响

- 场景：headless Chrome + CDP 验证 uni-app H5 页面 `uni.chooseImage → uni.uploadFile` 全链路（wofule 任务16 头像上传，verify13）。
- 现象：`DOM.setFileInputFiles({nodeId/files})` 后 input 的 change 事件已触发、`input.files.length=1`，但 uni-app H5 chooseImage 的 success 回调不执行 → 零 uploadFile 请求，链路断在选图步。

## 根因（事实+推断）

- 事实：改用 `Page.setInterceptFileChooserDialog` 拦截真实文件选择对话框、拿事件里的 `backendNodeId` 再 `DOM.setFileInputFiles({backendNodeId, files})` 后，chooseImage success 正常走到 uploadFile（verify13 24/24 全绿）。
- 推断：uni-app H5 chooseImage 动态创建的 input 与其回调绑定依赖真实选择器流程/节点生命周期；按 nodeId 注入绕过了它监听的通路。**机制未逐行证实，但两种注入方式对照结果稳定。**

## 最小修复（做法）

1. 点击触发 chooseImage 前先 `Page.setInterceptFileChooserDialog({enabled:true})`。
2. 点击后收 `Page.fileChooserOpened` 事件，取 `backendNodeId`。
3. `DOM.setFileInputFiles({files:[绝对路径], backendNodeId})`。
4. 断言上传请求与回包，而不是只断言 input.files。

## 验证命令与结果

- verify13（C:\Users\Admin\iconpark-render\verify13.mjs）：full 24/24、guest 8/8；multipart 上传 success:true、落盘 D:\upload\headpic\ 文件 SHA 与注入图匹配。
- 附带教训：HMR 重载会抹掉页面内注入的 instrumentation——断言脚本要在每次导航/重载后重新注入；dev 换进程后旧 bundle 需刷新重进。
- 附带事实：CDP 对 multipart 请求 `hasPostData:true` 但 `postDataLen:0`（不公布 body）；字段正确性靠服务端回包+落盘文件名断言。sockjs-client（webpack-dev-server HMR）在新 Chrome 报 `Permissions policy violation: unload is not allowed in this document.`，属浏览器策略提示，非应用报错。

## 适用范围与剩余风险

- 适用：任何 headless CDP 取证 H5 文件选择/上传链路（uni-app、原生 input 均可先试拦截法）。
- 剩余风险：不同 uni-app 版本 chooseImage 实现可能不同；拦截法失败时回退 nodeId 法并如实披露断言层级。

## 关联

- 档案：G:\AIrenwu\01_任务归档\2026-11-15_课程作业档案\01_报告\跨平台应用开发-档案.md（项14）
- 证据：C:\Users\Admin\iconpark-render\verify13-full.json / verify13-guest.json
