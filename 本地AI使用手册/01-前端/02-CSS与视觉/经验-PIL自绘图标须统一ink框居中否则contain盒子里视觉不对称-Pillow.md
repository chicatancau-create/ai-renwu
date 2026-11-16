---
title: "自绘扁平图标当 iconfont 替身：`background-size: contain` 缩放的是整张画布，图形不统一 ink 框就会大小不一、左右不齐；斜向粗线的单位向量要除以 hypot 而不是 √2"
date: 2026-11-15
domain: frontend
category: 01-前端/02-CSS与视觉
status: verified
severity: medium
stack: [Python, Pillow, uni-app H5, CSS ::before, iconfont]
tags: [自绘素材, ink 包围盒, contain, 光学对齐, PIL polygon, 抗锯齿]
---

# 问题：课件示例图要 iconfont 图标，素材拿不到 → 自己画四张 PNG，结果「大小不一、左边不齐、上下飘」

## 一句话结论

`background-size: contain` 等比缩放的是**整张画布**，不是图形。所以四张图放进同一个 50rpx 盒子后，
视觉大小与对齐完全由「图形在画布里的 ink 包围盒」决定 —— 必须把所有图形统一画进同一个图形框并让
**ink 中心 = 画布中心**，否则形状本身的胖瘦差异会直接体现为排列不齐。判据用 `im.split()[3]` 的 alpha
ink bbox，肉眼看图只能发现"不对"，量不出"差多少"。

## 触发条件与影响

- 项目：`跨平台应用开发/wofule`（uni-app Vue2，HBuilder X 5.33）「新生入学 APP 个人中心」拓展任务。
- 前置：示例图那套图标来自 iconfont，本机拿不到素材；工程里已有的写法是
  `.entry::after { content:""; width:50rpx; height:50rpx; background-image:url("/static/more.png"); background-size:contain; }`。
  补图标只能沿用同一机制（`::before` + `nth-child` 换 url），不引 iconfont、不引组件库。
- 影响：第一版四张图（名片 / 写字板 / 挂锁 / 便签+铅笔）在页面上看起来不是一套东西——名片偏扁、
  写字板偏高、便签那张整体往左上飘。

## 复现步骤

1. PIL 在 128×128 RGBA 上画四个图形，各按"形状自然尺寸"画（名片 104×72、写字板 100×110、便签 94×92）。
2. 存进 `static/`，CSS 用同一个 50rpx 盒子 + `background-size: contain`。
3. 操作：headless Edge 375×667@2x 截图，逐行量图标 ink 位置。
4. 实际结果（第一版，设备像素）：

   | 图标 | ink 宽×高（画布内） | ink 中心（画布内） | 渲染后中心 x | 渲染后左边线 x |
   |---|---|---|---|---|
   | 个人信息 | 104×72 | (64, 64) | 62.5 | 44 |
   | 订单列表 | 100×110 | (64, 61) | — | 46 |
   | 意见反馈 | 94×92 | **(57, 58)** | — | 44 |

   「意见反馈」的铅笔戳出便签左上角，把整个图形重心挪了 7 个画布单位 ⇒ 看上去和上面两行不对齐。

## 证据

- 量法：`a = im.split()[3]; xs = [x for x in range(128) if any(a.getpixel((x,y))>16 for y in range(128))]`，
  对 `xs/ys` 取 min/max 得 ink 框。**`getbbox()` 在这里不能用**——它按"非零像素"算，
  画布四角只要有半透明抗锯齿残留就返回整张画布，判不出图形实际占位。
- 统一图形框（x 16..112、y 16..112、中心 64,64）后：

  ```text
  info.png      ink x  15..112 (w= 98)  y  27..100 (h= 74)  center (63.5, 63.5)
  list.png      ink x  19..108 (w= 90)  y  15..112 (h= 98)  center (63.5, 63.5)
  password.png  ink x  19..108 (w= 90)  y   7..114 (h=108)  center (63.5, 60.5)   ← 未改，本来就彩色
  feedback.png  ink x  15..111 (w= 97)  y  16..112 (h= 97)  center (63.0, 64.0)
  ```

- 页面实测（设备像素，dpr=2）：四行图标中心 x = 62.5 / 63.0 / 62.5 / 62.5（差 ≤0.5px），
  左边线 = 44 / 46 / 46 / 44；每行相对行高的偏移一致（3.3 CSS px，与 `.entry::after` 的 `top:0.5em` 同基准）。
- 四张图都真加载：`getComputedStyle(e,'::before').backgroundImage` 指向对应 url，
  再用 `new Image()` 预加载回 `ok 128x128`；`curl` 四个地址各 200（2155~4800 B）。

## 根因分析

- 已确认根因：`contain` 只对**画布**等比缩放，图形在画布内的位置/尺寸差异被原样带进渲染结果。
- 排除过的假设：①「CSS 盒子没对齐」——`::before` 与 `::after` 用同一组 `left/right + top:0.5em`，
  四行盒子完全相同（实测盒宽都是 25px）；②「`padding-left` 把图标挤歪」——图标是 `position:absolute`，
  不受 padding 影响。
- 附带画坏的一次（真踩坑，**PIL 不报错**）：斜向"铅笔"用 `polygon` 手搓粗线，法向偏移写成
  `px, py = -(by-ay)/2**0.5*half, (bx-ax)/2**0.5*half`。除以 `√2` 只有在位移量恰好为 1 时才是单位化；
  实际位移 168px 时法向偏移被放大 168 倍 ⇒ 图标画成一坨占满画布的灰色箭头，脚本照常"保存成功"。
  正解：`L = math.hypot(bx-ax, by-ay)`，再 `px, py = -(by-ay)/L*half, (bx-ax)/L*half`。

## 最小修复

1. 定一个图形框，所有图形都画进去（本次 128 画布取 16..112，中心 64,64）；扁形状（名片）保持
   中心对齐即可，不必强行等高。
2. 抗锯齿：在 4 倍画布（512×512）上画，再 `resize((128,128), Image.LANCZOS)` 落盘；
   直接在 128 上画边缘是锯齿的，和工程里既有素材（128×128 RGBA）风格不一致。
3. 画完先拼一张 montage 目视，再谈数字——见关联记录。
4. 判"齐不齐"用 alpha ink bbox（中心 + 宽高），不要用 `getbbox()`。

```python
SS = 4                                   # 4 倍超采样再缩到 128
BOX = (16, 16, 112, 112)                 # 统一图形框，中心 (64,64)
def pencil(a, b, half, color):           # 斜向粗线：先白描边留空隙，再画本体
    L = math.hypot(b[0]-a[0], b[1]-a[1])         # ← 除以长度，不是 √2
    px, py = -(b[1]-a[1])/L*half, (b[0]-a[0])/L*half
    d.polygon([(a[0]+px, a[1]+py), (b[0]+px, b[1]+py),
               (b[0]-px, b[1]-py), (a[0]-px, a[1]-py)], fill=color)
def ink_bbox(im):                                # 判据：alpha，不是 getbbox()
    a = im.split()[3]
    xs = [x for x in range(128) if any(a.getpixel((x, y)) > 16 for y in range(128))]
    ys = [y for y in range(128) if any(a.getpixel((x, y)) > 16 for x in range(128))]
    return min(xs), min(ys), max(xs), max(ys)
```

配色（本轮定的，供续改）：个人信息 `#1296db`（与 `pages.json` 的 `tabBar.selectedColor` 同色）、
订单列表 `#f0983c`、意见反馈 `#e0637c`、修改密码沿用原来的绿锁（描边 `#405e6b` + 绿 `#40e699`）。

## 验证记录

- [x] 四张图 alpha ink 中心回到 (63.0~63.5, 63.5~64.0)，见上表。
- [x] headless Edge 375×667@2x 实测中心 x 差 ≤0.5 设备像素、左边线差 ≤2 设备像素。
- [x] 四张图 `new Image()` 预加载全 `ok 128x128`，`curl` 全 200。
- [x] 页面无 JS 异常（`Runtime.exceptionThrown` 计数 0）。
- [ ] **小程序 / App 端未验**：本轮只跑 H5。`::before` + `background-image: url("/static/*.png")`
      在小程序端能否解析本地路径，未在本机复现，别当成已通过。

## 可复用规则

1. **自绘位图当 iconfont 替身时，先定图形框再画形状**；"看起来不对称"几乎都是 ink 中心没对齐，不是 CSS 的问题。
2. **量 ink 框用 alpha 通道**（`split()[3]` 逐列判定），`getbbox()` 会被抗锯齿残留骗成整张画布。
3. **`contain` 盒子里，画布留白 = 隐形的 padding**：想让图标"更大"，改画布内图形框，不要改 CSS 盒子尺寸。
4. **PIL 手搓斜线：除以 `hypot`，不是 `√2`**；这类错误不抛异常，只能靠目视 + ink bbox 兜住。
5. **改素材不改写法**：本轮 `my.vue` 只加了 `::before` 与四条 `nth-child`，模板/数据/逻辑零改动，
   保持与工程既有 `.entry::after` 同一套机制（这是"看不出是 AI 写的"的关键约束）。

## 适用范围与不适用范围

- 适用：任何"自绘 PNG 当图标素材 + CSS `background-size: contain` 定位"的场景；uni-app / 小程序 / 网页均同。
- 不适用：真 iconfont（字体子集 + `content:"\e6xx"`）——那条路要素材文件，本轮正是因为拿不到才绕开。
- 例外：`background-size: cover` 或 `100% 100%` 时画布留白会被吃掉/拉伸，ink 框规则要重算。

## 剩余风险

- 素材是 PIL 画的扁平图形，与课件那套 iconfont 只能"神似"，细节（名片上横线条数、铅笔角度）对不上原图。
- 四张图未做深色模式适配（描边/留白用的白色 `#ffffff`，深色底上留白会显脏）。

## 关联

- 相关记录：[[03-通用/03-调试与验证/规则-判断图片内容必须目视打开不能靠亮度尺寸统计|判断图片内容必须目视打开，不能靠亮度尺寸统计]]、
  [[01-前端/02-CSS与视觉/踩坑-Tk画布图元不抗锯齿且烘图底材须取真实底色-Tk|Tk 画布图元不抗锯齿，烘图底材须取真实底色]]（同族：自绘位图的抗锯齿与底色）、
  [[03-通用/03-调试与验证/经验-课件截图反推rpx先按分隔线间距定标-uni-app|课件截图反推 rpx：先按分隔线间距定标]]（同一任务的尺寸来源）
- 相关分类：[[01-前端/02-CSS与视觉/README|CSS 与视觉]]
- 本机产物：素材已入库 `跨平台应用开发/wofule/static/{info,list,password,feedback}.png`；
  生成脚本在 %TEMP% 里，已被 11-11 的 Windows 更新清空（见 [[03-通用/04-工程规范与安全/踩坑-回退备份与取证放TEMP会被更新重启清空且日志会滚存|取证放 TEMP 会被清空]]），
  可复现的最小骨架已抄进本记录"最小修复"段。
