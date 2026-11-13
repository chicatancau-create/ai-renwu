/**
 * 宿主端：注册一个 `/preset` 斜杠命令，用来在**已经开始的会话**里切换智能体预设。
 *
 * 为什么必须有这一半：
 * 出厂客户端把会话标题栏的预设显示写成了只读标签（AgentPresetLabel），而且它的
 * 选择控制器 apply() 里有 `if (!session.blank) return UNCHANGED`，会在浏览器端
 * 直接把切换请求丢掉，连远程调用都不会发出。所以会话内切换只能绕开那条路径。
 *
 * 斜杠命令走宿主端 commands 服务，改完立刻生效，不需要刷新页面。
 * 宿主端的 `agent-preset/locked` 硬锁由 dsh-preset-unlock 负责放开。
 */

/** 命令名，输入 `/preset` 触发。 */
const COMMAND_NAME = 'preset'

/**
 * 出厂内置预设不带 name 字段，显示文案来自 locale 字典。
 * 这里照抄 @deepseek-ai/dsh-agent-presets 的 display.js 映射表，写成中文，
 * 让 `/preset` 列表和界面上看到的名字保持一致。
 */
const BUILT_IN = {
  standard: '标准模式',
  ptc: 'PTC 模式',
  minimal: '极简模式',
  cordis: '创造模式',
}

/**
 * 解析一条预设的显示名，与出厂 presetDisplayText 同语义：
 * 内置预设走中文映射，自定义预设用作者自己写的名字。
 * @param preset 预设表里的一行。
 * @returns 显示名。
 */
function displayName(preset) {
  const built = BUILT_IN[preset.id]
  const shipped =
    built !== undefined &&
    (preset.trust === 'system' || preset.name === undefined || preset.name === preset.id)
  if (shipped) return built
  return preset.name ?? preset.id
}

/**
 * 硬依赖：commands 提供斜杠命令注册，agentPresets 提供预设读写。
 * 声明成 inject 后，Cordis 会等这两个服务就绪再激活本插件。
 */
export const inject = ['commands', 'agentPresets']

/**
 * 注册 `/preset` 命令。
 * @param ctx 宿主插件上下文。
 */
export function apply(ctx) {
  // agents 是可选的：只用来把命令拿到的 { id } 换回带 ctx/session 的完整 Agent。
  const agents = ctx.get('agents')

  ctx.effect(() =>
    ctx.commands.register({
      name: COMMAND_NAME,
      description: '切换本会话的智能体预设（模式）：/preset 查看列表，/preset <id> 切换',
      input: { hint: '[预设 id]' },
      handler: async (invocation) => {
        const raw = invocation.rawInput.trim()

        // 命令只保证 agent.id；select() 还需要 agent.ctx 和 agent.session，
        // 所以优先从 agents 注册表取回完整的 live Agent，取不到就用命令给的对象。
        const live = agents === undefined ? undefined : agents.get(invocation.agent.id)
        const agent = live ?? invocation.agent
        if (agent.ctx === undefined || agent.session === undefined) {
          return { kind: 'error', text: '找不到这个会话对应的 Agent，无法切换。' }
        }

        const presets = await ctx.agentPresets.list()
        const roster = Array.isArray(presets) ? presets : []

        // 无参数：列出可选预设，标出当前在用的那个。
        if (raw === '') {
          const current = ctx.agentPresets.composedPreset(agent.ctx)
          const lines = roster.map((preset) => {
            const mark = preset.id === current ? '  ←当前' : ''
            const name = displayName(preset)
            const broken = preset.broken === undefined ? '' : `（不可用：${preset.broken}）`
            return `- \`${preset.id}\` ${name}${broken}${mark}`
          })
          return {
            kind: 'success',
            text: [
              '可用预设：',
              ...lines,
              '',
              '用 `/preset <id>` 切换本会话，例如 `/preset team`。',
            ].join('\n'),
          }
        }

        // 允许直接用中文名切换，省去记 id。
        const target =
          roster.find((preset) => preset.id === raw) ??
          roster.find((preset) => displayName(preset) === raw)
        if (target === undefined) {
          const known = roster.map((preset) => `\`${preset.id}\`（${displayName(preset)}）`).join('、')
          return { kind: 'error', text: `没有名为 \`${raw}\` 的预设。可用：${known}` }
        }
        if (target.broken !== undefined) {
          return { kind: 'error', text: `预设 \`${displayName(target)}\` 当前不可用：${target.broken}` }
        }

        try {
          const committed = await ctx.agentPresets.select(agent, target.id)
          const finalName = displayName(roster.find((preset) => preset.id === committed) ?? target)
          return { kind: 'success', text: `已切换到「${finalName}」。` }
        } catch (cause) {
          const message = cause instanceof Error ? cause.message : String(cause)
          return { kind: 'error', text: `切换失败：${message}` }
        }
      },
    }),
  )
}
