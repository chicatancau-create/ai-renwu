# AI 协作与提示词

适合记录上下文组织、提示词、工具调用、子任务交接、事实核验和长期记忆接入问题。

## 记录

- [[规则-WorkBuddy技能发现机制与本地技能安装位置]]（verified，2026-10-13）— 本地技能放 `~\.workbuddy-ai\skills\<name>\SKILL.md` 即自动发现；缓存约十几分钟自刷新、无需重启；`description` 决定"能否默认调用"
- [[规则-技能库已收录逆向技能只放指针]]（verified，2026-10-11；2026-10-12 复扫并就地标注过时项）— 技能库新增 `reverse-trace` / `reverse-wechat-miniapp`，手册只放指针与调用边界
- [[规则-逆向工具箱清单与后端选型决策表-MCP]]（verified，2026-10-11）— 6 个包的身份、后端选型决策表与本机可启动性实测
- [[规则-本地手册接入DSH成为默认前置与写Markdown的编码坑]]（verified，2026-10-19）— 想让手册「默认被用」要写 `~/.dsh/AGENTS.md`，不是只改 skill description；DSH 的 preset 覆盖会整份替换、`agent-instructions` 无法在 preset 内重挂；PowerShell 拼串写含反引号的 Markdown 会被拆行，应落 Node 脚本执行；沙箱 `workspace-write` 拒写 E 盘时改用 Node/Python 通道
- [[规则-桌面快捷方式消失先查DeskBox勿重建-Windows]]（verified，2026-10-31）— 用户会把桌面 `.lnk` 归档进 `E:\DeskBox\<分类>\`，桌面计数为 0 不等于被删；复查第一步是 `glob(r'E:\DeskBox\**\*.lnk', recursive=True)`，命中就不重建；交付汇报要同时给出程序本体绝对路径
- [[规则-本机技能默认只开两个由总路由按需读取]]（verified，2026-11-15）— 用户定规：所有 Agent 默认只加载 `headroom` + `skill-router`；全量库 `D:\Skills` 与默认窗口 `D:\Skills-active` 两层，12 个技能根接法；路由靠**直接 read SKILL.md**（Agent 会话开始就快照技能列表，改目录看不见）；cc-switch 的 `enabled_<agent>` 只管它自己表里那 9 个，管不到统一库；改接技能根只能 inject 不能 rmdir 重建（WorkBuddy 往根里写状态 JSON）


- [[规则-国内版与国际版Qoder两套记忆目录完全独立只能单向拷入并校验]]（verified，2026-11-15，severity medium）— `.qoder` 与 `.qoder-cn` 各存一份记忆，settings.json 无共享项、无联接；要搬只能 `cp -n` 单向拷 + 手工合并索引，然后两项脚本校验（逐文件查是否入索引、`diff -rq` 只剩 Only in 目标）；**别用 mklink /J 实时共用**（两边同写 MEMORY.md 会互相覆盖）；同名文件不等于重复（`reference-zongce-weiji-table.md` 用户级与项目级是两条不同记录）；国际版索引本身漏了 2 条，补完才 70/70 对齐
- [[经验-Qoder浏览器Agent的evaluate恒null与自绘单选要点label]]（verified，2026-11-15）— `tab.playwright.evaluate` 在本机这版恒返回 null，读 DOM 用 `domSnapshot()`；自绘单选要点 `label:has(input[value=...])`；调试器断开后 agent 临时页被回收；对外写操作要刷新回读 + 独立验证
- [[规则-派修复工人要配可复跑裁判并禁止它改裁判]]（verified，2026-11-15）— brief 里写「1280px 观感不得退化」这种软约束，会让工人据此**拒绝修一个真实缺陷**（它算出修它要动轨道，判为与约束冲突）；把遮挡像素量化进裁判脚本再派单，同一工人就同时满足了 over=0 与 cover=0。另含：并行分工靠「文件归属互不重叠 + 契约写进 brief」零冲突、工人报绿要独立复跑、交付截图要与破坏性测试分趟、收尾扫被测项目根目录、多会话共用仓库时默认不提交
- [[规则-多AI同仓审查交接三件套与续接先核时钟]]（verified，2026-11-12，severity medium）— 发现文档+必读指针+处置建议;已闭标✅与不要重查清单;续接先核 date/HEAD
- [[规则-不要自作聪明先按用户说的目标扫数据]]（verified，2026-11-15 登记并补 frontmatter）— 用户已给出目标时，第一步是按目标把相关数据源全扫一遍再下结论。`verified` 的依据是**来源与案例**（用户明示 + 一次真实反面案例：Motrix 被连猜三个无关方向），行为规则不适用「跑一遍复现」
- [[规则-全机AI共享全局记忆存D盘Skills库并接线各Agent]]（verified，2026-11-19，severity medium）— 共享记忆实体 `D:\Skills\global-memory\`（125 条 + MEMORY.md 索引），接线走各 Agent 全局指令文件而非技能目录；单向 cp -n + sha256 + 索引合并 + orphan 检查；30 个同名冲突逐文件 diff 三分类，国内独有且缺失的内容以带日期附录逐字追加（8 文件 +62 行）；随技能库双远端私有备份；禁 junction 实时共用
