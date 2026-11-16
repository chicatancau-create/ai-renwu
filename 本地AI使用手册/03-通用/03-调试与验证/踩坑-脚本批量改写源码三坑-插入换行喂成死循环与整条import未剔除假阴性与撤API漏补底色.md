---
title: "踩坑：脚本批量改写源码三坑——插入换行喂成死循环、整条 import 未剔除导致假阴性、撤 API 漏补底色与签名"
date: 2026-11-15
domain: common
category: 03-调试与验证
status: verified
severity: high
stack: [Python, ArkTS, Git]
tags: [批量改写, 正则, 死循环, 静态检查, 假阴性, 撤API, 幂等]
---

# 问题：三个坑都在同一次「脚本批量撤 API」里踩到，且都不报错

## 一句话结论

用脚本批量改写源码时：① 替换里插入 `\n` 会让 `\s{4,}` 这类模式在下一轮匹配到自己刚插的换行，`while re.search(...)` 变成**幂等死循环**；② 检查"导入了但没用"时只删以 `import ` 开头的**行**，跨行 import 的续行还留在正文里，于是每个名字都被自己匹配成"已使用"，**检查器永远报 0**；③ 批量删掉某个属性调用后，它原本承担的职责（背景色、方法参数）不会自动补，编译期才炸。

## 触发条件与影响

- 项目或功能：一次性把 15 个源文件里的某批 API 调用（`.stateStyles` / `.animation` / `.shadow` / `.linearGradient` …）全部撤掉
- 环境与版本：Windows + Git Bash + 系统 Python（`python -X utf8`），ArkTS 工程
- 触发条件：写脚本做「正则删链式调用 + 拆粘连行 + 清理未用导入」三件事
- 影响范围：一个坑让任务卡死需人工 kill；一个坑让前几轮"静态检查通过"的结论全部作废；一个坑让构建在最后一轮才失败

## 复现步骤与现象

### 坑 1：拆粘连行的循环不收敛

```python
line = re.sub(r'\)\s{4,}(?=[.\}\)]|[A-Z$])', lambda m: ')\n' + ind, line)
while re.search(r'\)\s{4,}\.', line):          # ← 死循环
    line = re.sub(r'\)\s{4,}\.', lambda m, i=ind: ')\n' + i + '.', line)
```

第一步已把 `)      .foo(` 变成 `)\n      .foo(`，而 `\s` 能匹配 `\n`，`\s{4,}` 又正好吃掉「换行 + 6 个空格」，替换结果与输入等价 ⇒ `while` 条件永真。命令被后台化、手动 kill，前 11 个文件已写盘、后面的没写，**处于半改状态**。

> 处置：改成**逐行 tokenizer**（自己数括号与空格、一次成型），不用 `while + re.sub` 收敛；半改状态用改前备份的 `cp` 恢复，而不是再跑一遍脚本。

### 坑 2：未用导入检查器假阴性

```python
body = '\n'.join(l for l in s.splitlines() if not l.strip().startswith('import '))
```

对单行 `import { A, B } from 'x'` 有效；对跨行块只删掉首行 `import {`，续行 `  A,`、`  B,` 仍在 `body` 里 ⇒ 每个名字都能匹配到自己 ⇒ 连续几轮都报 `total unused = 0`。

修法是**剔除整条语句**再检查：

```python
imp_stmt = re.compile(r'^import\s*\{[^}]*\}\s*from\s*[\'"][^\'"]*[\'"]\s*$', re.M)
body = imp_stmt.sub('', s)
```

修好后立刻查出一个真问题（某页面撤掉用法后残留的 `SPACE_XS` 导入）。

### 坑 3：撤 API 后职责没人接

- 删掉 `.linearGradient({...})`：这个调用原本就是容器的**唯一背景**。删完标题条/价格条变成透明，界面会"字浮在白底上"。必须同批补 `.backgroundColor(PRIMARY)`。
- 删掉 `@Builder itemEnd(index: number, name: string)` 里用到 `name` 的逻辑，调用点仍传两个参数 ⇒ 编译报 `Expected 2 arguments, but got 1`；反过来把参数删了又忘了加类型 `itemEnd(index)` ⇒ 报 `arkts-no-any-unknown`。**签名、调用点、类型标注三处要一起改**。
- 同一轮里 `if (this.loading) { LoadingProgress()... }` 删掉组件后留下空 `if` 块，编译能过但逻辑空转，得手动换成文字提示。

## 证据

```
# 坑 2 修复前后
（修复前，连续 3 轮）total unused = 0
（修复后）UNUSED pages\me\Index.ets SPACE_XS / total unused = 1

# 坑 3 的编译错误
Error Message: Expected 2 arguments, but got 1. At File: .../pages/test/ListPage.ets:102:31
Error Message: Use explicit types instead of "any", "unknown" (arkts-no-any-unknown) At File: .../AddressPage.ets:23:20

# 坑 1 的处置
Command exceeded its timeout and was moved to background ... killed
```

## 最小修复（可复用动作）

1. 批量改写前先 `cp -r` 整目录备份到 TEMP，且**替换全部命中才写盘**（脚本里用 `assert old in s` / `raise SystemExit`，缺一处就整文件不写）。
2. 拆行/删调用一律写成"一次成型"的 tokenizer 或有界循环（`for _ in range(N)`），禁止 `while re.search(自己插入的文本)`。
3. 静态检查脚本本身要**做负对照**：故意留一个未用导入，确认它能报出来，再信它的 0。
4. 撤 API 时同批检查三件事：该调用是否承担了背景/尺寸等**唯一职责**；方法签名与所有调用点；参数类型标注是否还在。
5. 半改状态恢复：用本轮备份覆盖，别用"再跑一遍脚本"碰运气。

## 验证记录

- [x] 编译：`hvigorw clean` + `assembleHap` → BUILD SUCCESSFUL，32/33 任务执行、ERROR 0
- [x] 静态检查：修复后的检查器报出 1 个真问题并清零；`grep` 复扫被撤 API 的关键字 = 0 处
- [x] 产物核对：hap 内 `DotIndicator`、`LoadingProgress` 符号计数从 ≥1 变 0
- [ ] 运行时目视：无模拟器镜像，未做

## 适用范围与不适用范围

- 适用：任何语言的大规模机械改写（撤依赖、换 API、统一命名、格式化）
- 不适用：需要理解语义的重构（这类要逐文件人工改或小步提交）

## 剩余风险

`\s` 类模式与"插入换行"的组合是通用陷阱，本次只在自己写的两个脚本里排掉；仓库里若还有历史脚本用同样写法，需按第 3 条做负对照才能信。

## 关联

- 相关记录：[[03-通用/03-调试与验证/踩坑-提交前审查两坑-全暂存区混入空文件与课程样例误判]]
- 相关分类：[[03-通用/通用索引]]
- 相关代码、命令或文档：本次三个脚本分别是「删链式调用」「拆粘连行」「查未用导入」，正文各附最小可用片段
