# 工程规范与安全

适合记录代码审查、敏感信息、依赖风险、文件保护、回滚和交付流程问题。

## 记录

- [[踩坑-PowerShell5.1读无BOM的UTF8脚本中文变乱码]]（verified，2026-10-10；2026-10-14 补双 BOM 形态）— Windows 上给 PowerShell 的 .ps1 固定 utf-8-sig + CRLF；加 BOM 只走 encoding 一条通道，正文里别手写 `﻿`
- [[踩坑-cmd入口脚本判管理员与choice默认键取值]]（verified，2026-10-12）— 自我提权 + 不可逆命令的 .cmd 判据：fltmc 而非 net session、choice 默认档必须落在取消
- [[踩坑-GetContent默认按代码页解码致UTF8中文回显乱码]]（verified，2026-10-13）— 乱码是"读"出来的不是"显示"出来的；判文件好坏只认 ReadAllText(UTF8) 或严格解码器，不认 Get-Content
- [[踩坑-CreateMutexW后未紧邻读GetLastError致单实例守卫静默失效]]（verified，2026-10-14）— `GetLastError()` 必须是紧随 API 调用的第一条语句；静默失效的守卫只能靠外部计数发现，验收要显式"起两次数进程"
- [[规则-AtomGit与GitHub差异与国内推送判据]]（verified，2026-10-15）— gitcode.com 与 atomgit.com 同一后端；国内站直连别挂代理、GitHub push 才要代理；判域名可用只认 git smart-HTTP 行为测试


- [[规则-规则类改动先写死判定式并核对注释与代码一致]]（verified，2026-10-19）— 口语需求先落成 a/b/c 判定式；**注释里的公式在代码里找不到就是 bug**；附一次改 4 稿的自省记录
- [[踩坑-提交前审查两坑-全暂存区混入空文件与课程样例误判]]（verified，2026-11-13）— git commit 提交整个暂存区：AM 空文件会混入无关提交，提交前重新 add + numstat 验证；排除「运行时产物」前先 grep 引用：代码读它+无代码生成它=课程样例必须入库
- [[规则-工作区大纲与归类铁律]]（verified，2026-11-15；2026-11-16 更新为 7 类）— G:\AIrenwu 根只允许 7 类文件夹（含本地AI使用手册）+README/.gitignore；创建任务先建 01_任务归档/YYYY-MM-DD_任务名/ 标准分层；移不动=停→移→恢复；历史证据快照不改写
- [[规则-批量搬迁先patch引用后搬与证据快照排除]]（verified，2026-11-15）— 批量搬迁：dry-run→镜像备份→先 patch 引用（长名优先+边界+双斜杠+$PSScriptRoot）后搬→守恒断言；证据/备份/node_modules 排除 patch；活体清单 schtasks/Run/快捷方式/pnpm link:/手册
- [[踩坑-删联接目录会跟随联接回收真源须靠回收站元数据取证]]（verified，2026-11-15）— **用资源管理器删「全是联接」的目录会跟随联接把真源一起回收**（本机技能库一夜被清空三次）；判据「进回收站⇒shell 删除，不是 rmtree」；解析 `$I` 元数据（version/size/FILETIME/UTF-16 原路径）取证并原样恢复 13 文件；`D:\$RECYCLE.BIN\S-1-5-18` 属 SYSTEM 须跳过；加固＝联接图之外留真实镜像 + 20s 自愈循环（实测两次故障注入均一轮修复）
- [[踩坑-gitattributes晚于首次add致备份CRLF被规范化]]（verified，2026-11-15）— **push 返回 0 不等于备份可用**：`.gitattributes` 晚于首次 `git add` 致 79 文件 CRLF→LF 入库；`git rm -r --cached .` 不保证清空索引，修法 `git add --renormalize .`；**验收标准＝从远端克隆回来逐文件 sha256 一致**（4 远端 13314 文件全绿）；git 在 Windows 把 pack 设只读，rmtree 须 onerror chmod 重试
- [[规则-技能库上传前按许可排除且私有仓库不豁免]]（verified，2026-11-15）— 7 个技能永不上远端：docx/pdf/pptx/xlsx（Anthropic 专有，明文禁止 Services 外保留副本+转移第三方）、两个逆向包（无 LICENSE 限本机自用）、webapp-building（泄露内容无许可）；**私有仓库不豁免**；同源副本要一起判（173/175 字节相同却丢了限制条款）；排除要双层 `.gitignore` + 提交前暂存路径检查；密钥扫描命中必须逐条打开看（测试夹具大量误报）
- [[踩坑-pwsh管道喂python把UTF8中文重编码致JSON假错]]（verified，2026-11-15，severity medium）— `Get-Content x.json -Raw | python -c "json.load(sys.stdin)"` 报 `Expecting ',' delimiter` / `Invalid control character`，但同一文件 `open()` 直读完全合法：PowerShell 5.1 按系统代码页解码 UTF-8 字节再编码写管道，**108 字节的手写 JSON 经管道变 143 字节**，中文变 `\xe6\xb6\x93\xee\x85\x9f` 这种碎片并生出控制字符。判据只需一比：文件字节数 vs 管道收到字节数；修法＝**传路径不传内容**（让子进程自己 `open(path, encoding='utf-8')`），`-Encoding UTF8` 只修解码不保证不重编码
- [[规则-通用加宽规则击穿形变硬约束须按应用名单制]]（verified，2026-11-15，severity medium）— "窗口竖向太窄"是**形状**，"这个应用接受被拉宽"是**属性**，形状推不出属性：把单应用修复写成通用规则后，`test_extreme_ratios` 1499 例 deform≤1.25 硬约束被大面积击穿（2124x2400→1718x1340 deform 1.43）、记事本 1000x700 被误加宽、用户手改的 900x700 又被拉走，全量 15/19；撤回成 `wide_apps` 名单制（4 项 ×0.78）后 19/19。规则：**凡"故意违反既有不变式"的优化一律按对象登记，不按形状泛化**；泛化前先跑最极端那组约束测试，被击穿=方向错而不是参数没调好；白名单分支必须验幂等（加宽后落回"按比例装进红圈"档反算回同值）
- [[规则-清理归档前先反查三类引用]]（verified，2026-11-15，severity high）— **"看起来没用"≠"真的没用"**：删前必查 ① 计划任务/Run 是否指向 ② 脚本/文档是否引用 ③ 是否文档写明的回滚点。实测 6 个旧 `.bak` 是 `rollback.ps1` 的**默认回滚目标**（删了回滚直接 exit 2）；归档目录里的 `watch.py` 仍被 `WindowCenter` 任务跑着（删了监视器失效）。只有 `__pycache__` 与经哈希证实的重复副本可无条件删
- [[规则-进别人仓库先读结构表再落盘-目录命名]]（verified，2026-11-15）— **目录名=那条线"是什么"，不是"这次做了什么"**：落盘前先读 README 结构表/AGENTS.md，按已有分类线归位（按语言分线的仓库里，网页产物属 `Web/`，根目录不是任务暂存区）；文件名跟同级风格走，免得第二个页面撞名；结构变了同步改结构文档；搬已跟踪的文件用 `git mv` 且只针对具体路径，别 `git add <目录>` 卷进别人的未提交改动
- [[踩坑-bat内嵌PowerShell探针的marker与readkey空路径及pid只读]]（verified，2026-11-11）— GBK bat 内嵌 PS 探针用 `rem~`+`delims=~`（`rem#` 会吞注释 `#`）；`:readkey` 先判空路径；PS 避开只读 `$pid`；插 YAML 读同级缩进
- [[规则-清理会话垃圾前先比对交付件与导出原件]]（verified，2026-11-15，severity high）— 会话记录里的「交付件=最新导出件」只代表生成当时；用户手工编辑后页数/大小/MD5 会漂移。清理前递归比较两者，发现用户新增页或空白页只报告，不拿旧导出件覆盖当前交付；历史中间件按白名单删除，清理后复测交付哈希

