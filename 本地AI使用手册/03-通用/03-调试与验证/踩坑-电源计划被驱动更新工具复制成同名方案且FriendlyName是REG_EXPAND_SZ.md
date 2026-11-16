---
title: "Driver Booster 每运行一次就多复制一份同名电源方案；FriendlyName 是 REG_EXPAND_SZ 且内建方案存的是间接字符串"
date: 2026-11-15
domain: common
category: 调试与验证
status: verified
severity: medium
stack: [Windows 11, powercfg, 注册表, IObit Driver Booster]
tags: [电源计划, 注册表清理, 重复判定, 非提权, 复发]
---

# 问题：`powercfg /list` 只显 2 个方案，注册表里却有 18 个电源方案键

> 2026-11-03 定位并删除 9 个、2026-11-15 用重建的脚本复测。

## 一句话结论

第三方「驱动更新 / 系统优化」类工具（本机为 IObit Driver Booster，装在 `D:\IObitDriverBooster`）
会**每次运行都 import 一份内容完全相同的电源方案**，UI 不显示、卸载也不回收，于是注册表里越堆越多。
判「重复」不能靠名字，要把 `powercfg -query <GUID>` 的输出**归一化后取哈希**；
删要用 `powercfg -delete`（**非提权就能删**，比 `reg delete` 干净，会连子键一起收），
读名字时注意 `FriendlyName` 是 `REG_EXPAND_SZ`，而且内建方案存的是 `@%SystemRoot%\...` 间接字符串，不是人名可读的名字。

## 触发条件与影响

- 项目或功能：本机性能/省电方案；用户做了一次系统优化后怀疑「电源计划是不是变多了」
- 环境与版本：Windows 11 28000；`D:\IObitDriverBooster`（目录 mtime 2026-11-02）
- 触发条件：Driver Booster 每次运行导入同名方案；UI 只显示「平衡/高性能」这类被标记为内建或活动的方案
- 影响范围：`HKLM\SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes` 下 18 个方案键，其中 4 份逐字节相同

## 复现步骤

1. 前置条件：装过并运行过 Driver Booster
2. 操作或命令：
   ```bash
   powercfg /list                              # 只看得到 2 个
   reg query HKLM\SYSTEM\CurrentControlSet\Control\Power\User\PowerSchemes   # 18 个键
   python power_schemes.py                     # 归一化哈希分组
   ```
3. 预期结果：UI 与注册表条目数一致
4. 实际结果：`power_schemes.py` 把 18 个键按内容指纹分组，出现一组 4 个字节指纹完全相同的方案，
   名字分别带 `Plan` / `Overlay` / `v2` 等后缀；用 `reg query ... /f FriendlyName` 按 `REG_SZ` 匹配则**一个都读不到**

## 证据

- 11-03 实测：18 个方案键 → 归一化哈希后 4 份完全相同 → 删 9 个（含 4 份重复中的 3 份、5 个已无对象的残留），
  每个删除 `powercfg /delete` 返回 rc=0 且复验键消失。
- 11-15 复测（`python power_schemes.py` 原样输出）：

  ```
  共 9 个方案键，当前活动 = 30e90e4f-...-6127a8238648
  30e90e4f-...  Performance  a38e5feb458dbfb9  0x0  活动   唯一
  381b4222-...  平衡         ac9b3df77f8174bd  0x0  内建   唯一
  66666666-...  v2           d9d8325b53e923f8  0x0         唯一
  8c5e7fda-...  performance  c121255f550cf80a  0x0  内建   唯一
  961cc777-...  Overlay      2cbbb374e8a3e824  0x0         唯一
  a1841308-...  saver        5eac290de341dfa3  0x0  内建   唯一
  c670b6e6-...  Plan         aac4a73304ca470c  0x0         唯一
  ded574b5-...  Overlay      77010ca09d6e173d  0x0         唯一
  e9a42b02-...  Performance  dbf71929a53f3414  0x0  内建   唯一
  没有内容重复的方案。
  ```

  18 − 9 = 9，数量对得上；**8 天无复发**，同期 `D:\IObitDriverBooster` 目录 mtime 仍是 11-02，说明没再运行过。
- `reg query` 直接看值类型：`FriendlyName REG_EXPAND_SZ`（非 `REG_SZ`）；内建那条读回来是
  `@%SystemRoot%\system32\...`，`powercfg -getactivescheme` 才给出人名「卓越性能」。

## 根因分析

- 已确认的根因：Driver Booster 用 `powercfg -import` 落盘一份新方案（每次得到新 GUID，内容不变），
  且从不回收旧的；UI 只列内建 + 活动 + 未隐藏的，所以看不出注册表在膨胀。
- 排除过的假设：Windows 自身更新导致方案增多（同期无相关事件）；用户手工创建（4 份同名且字节完全相同，人手做不到）。
- 问题归属：**环境或依赖**（第三方工具行为）。
- 判据要点：`Attributes` 全是 `0x0`，所以**名字叫 `Overlay` 不代表它是 AC 电源覆盖方案**，别按名字归类。

## 最小修复

1. 只删「非内建 + 非当前活动 + 内容与他项重复或已无对象」的键：
   `python power_schemes.py --delete <GUID> --yes`（脚本对微软内建 4 个 GUID 与当前活动方案硬拒绝）。
2. 删除前用 `--backup DIR` 导出方案键与名字清单，**DIR 不得在 TEMP**（脚本内置拒绝，见关联记录）；
   注意 `.reg` 只是留证，**方案名无法靠 `powercfg -duplicatescheme` 还原**，所以名字清单要单独留。
3. 复发就再跑一次；真正的止血是**不再运行 Driver Booster**（本机驱动已够用）。

## 验证记录

- [x] 删除当时：9 个 `powercfg /delete` 全部 rc=0，复验注册表键数 18 → 9
- [x] 11-15 复测：`python power_schemes.py` 输出 9 个键、无重复组（上方证据块）
- [x] 脚本自检：`py_compile` 通过；`--backup` 指向 TEMP 时返回 3 并拒绝（本机实测该分支逻辑）
- [x] 未产生副作用：`powercfg -getactivescheme` 仍是 `30e90e4f`（卓越性能），睡眠/硬盘关闭设置未变
- [ ] 未再运行 Driver Booster 以验证「运行即复发」这一条（**故意不跑**：会改驱动栈，属于高风险动作；该结论来自 11-03 观察到它每次运行都留一份同名方案的行为模式，尚未在本机二次复现）

## 可复用规则

1. 判「注册表里重复条目」时，**比内容不比名字**：`powercfg -query <GUID>` → 去掉 GUID 与十六进制值 → 折叠空白 → sha256。
2. 删电源方案一律用 `powercfg -delete <GUID>`，非提权可用；不要用 `reg delete`（会留下 powercfg 缓存的视图不一致）。
3. 读方案名先按 `REG_EXPAND_SZ` 解析，并对 `@` 开头的间接串做名字表兜底。
4. 每轮体检要记「键数 + 当前活动 GUID」两个数，下次才能证明有没有复发（本条：18 → 9 → 9）。

## 适用范围与不适用范围

- 适用：任何 Windows 机器上「UI 看不到但注册表越堆越多」的方案/配置类膨胀排查，尤其是装过优化类软件的机器。
- 不适用：`ActiveOverlayAcPowerScheme`、`dcsettingsindex` 这类系统 overlay 的正确性判断；也不适用于删除用户手工调过参数的方案——
  内容指纹相同才敢删，只差一个参数值的相似方案要保留。

## 剩余风险

- `66666666-6666-6666-6666-666666666666`（名字 `v2`）与两个 `Overlay`、一个 `Plan` 内容互不相同，无法证明是垃圾，
  **按「只删可证明重复」的原则保留**（11-15 实测仍在）。若日后要删，需要用户提供来源。
- Driver Booster 若被再次运行仍会重新堆积，本机没有拦它的机制。

## 关联

- 相关记录：[[03-通用/04-工程规范与安全/踩坑-回退备份与取证放TEMP会被更新重启清空且日志会滚存]]、
  [[03-通用/04-工程规范与安全/规则-清理归档前先反查三类引用]]
- 相关分类：`03-通用/03-调试与验证`
- 相关代码、命令或文档：`G:\AIrenwu\脚本库\09_机器体检与垃圾扫描\power_schemes.py`
