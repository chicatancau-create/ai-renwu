/**
 * 离线验证 `/preset` 命令的处理器逻辑。
 *
 * 不依赖 DSH 运行时：用假的 ctx / commands / agentPresets / agents 把 apply()
 * 跑起来，抓住注册进来的 handler，再逐个场景调用它。
 *
 * 运行：node test-command.mjs
 */

import { apply, inject } from './index.js'

let pass = 0
let fail = 0

function check(name, condition, detail) {
  if (condition) {
    pass += 1
    console.log(`  ✓ ${name}`)
  } else {
    fail += 1
    console.log(`  ✗ ${name}${detail === undefined ? '' : `  →  ${detail}`}`)
  }
}

/**
 * 搭一个最小可用的宿主环境。
 * @param options 覆盖项：预设表、当前预设、live agent、select 行为。
 */
function makeEnv(options = {}) {
  const roster = options.roster ?? [
    { id: 'standard', name: '标准', isDefault: true },
    { id: 'solo', name: '单人交付' },
    { id: 'team', name: '团队协作' },
    { id: 'broken-one', name: '坏的', broken: '加载失败' },
  ]

  const calls = { select: [], list: 0 }

  const registry = {
    async list() {
      calls.list += 1
      return roster
    },
    composedPreset() {
      return options.current ?? 'standard'
    },
    async select(agent, id) {
      calls.select.push({ agent, id })
      if (options.selectThrows === true) throw new Error('agent-preset/locked: This session has already started')
      return options.selectReturns ?? id
    },
  }

  const agent = {
    id: 'sess-1',
    ctx: { marker: 'agent-ctx' },
    session: { append() {} },
  }

  const registered = []
  const commands = {
    register(definition) {
      registered.push(definition)
      return () => {}
    },
  }

  const ctx = {
    commands,
    agentPresets: registry,
    get(name) {
      if (name === 'agents') {
        return options.noAgents === true ? undefined : { get: (id) => (id === 'sess-1' ? agent : undefined) }
      }
      return undefined
    },
    effect(callback) {
      const disposer = callback()
      return () => disposer?.()
    },
  }

  apply(ctx)
  return { registered, calls, agent, roster }
}

/** 用给定 rawInput 调用注册进来的 handler。 */
async function invoke(env, rawInput, agentOverride) {
  const definition = env.registered[0]
  return definition.handler({
    commandId: 'cmd-1',
    agent: agentOverride ?? { id: env.agent.id },
    rawInput,
    attachments: [],
    signal: new AbortController().signal,
  })
}

console.log('场景 1：插件声明了正确的注入依赖')
{
  check('inject 含 commands', inject.includes('commands'))
  check('inject 含 agentPresets', inject.includes('agentPresets'))
}

console.log('\n场景 2：apply() 注册了名为 preset 的命令')
{
  const env = makeEnv()
  check('注册了 1 条命令', env.registered.length === 1, String(env.registered.length))
  check('命令名为 preset', env.registered[0]?.name === 'preset', env.registered[0]?.name)
  check('有描述', typeof env.registered[0]?.description === 'string' && env.registered[0].description.length > 0)
}

console.log('\n场景 3：`/preset` 无参数 → 列出全部预设并标出当前')
{
  const env = makeEnv({ current: 'solo' })
  const result = await invoke(env, '')
  check('返回 success', result.kind === 'success', result.kind)
  check('列出 4 个预设', ['standard', 'solo', 'team', 'broken-one'].every((id) => result.text.includes(id)))
  check('标出当前预设 solo', result.text.includes('`solo` 单人交付  ←当前'), result.text)
  check('标出不可用预设', result.text.includes('（不可用：加载失败）'))
  check('没有调用 select', env.calls.select.length === 0)
}

console.log('\n场景 4：`/preset team` 切换成功')
{
  const env = makeEnv()
  const result = await invoke(env, 'team')
  check('返回 success', result.kind === 'success', result.kind)
  check('文案用中文名「团队协作」', result.text.includes('团队协作'), result.text)
  check('调用了 1 次 select', env.calls.select.length === 1)
  check('select 收到完整 Agent（带 ctx）', env.calls.select[0]?.agent?.ctx?.marker === 'agent-ctx')
  check('select 收到正确 id', env.calls.select[0]?.id === 'team')
}

console.log('\n场景 4b：内置预设用官方中文名显示')
{
  const env = makeEnv({ roster: [
    { id: 'standard', trust: 'system', isDefault: true },
    { id: 'ptc', trust: 'system' },
    { id: 'minimal', trust: 'system' },
    { id: 'cordis', trust: 'system' },
  ], current: 'cordis' })
  const result = await invoke(env, '')
  check('显示「标准模式」', result.text.includes('标准模式'), result.text)
  check('显示「PTC 模式」', result.text.includes('PTC 模式'))
  check('显示「极简模式」', result.text.includes('极简模式'))
  check('显示「创造模式」', result.text.includes('创造模式'))
  check('不出现裸 id', !result.text.includes('- `standard` standard'), result.text)
}

console.log('\n场景 4c：可以直接用中文名切换')
{
  const env = makeEnv({ roster: [
    { id: 'standard', trust: 'system' },
    { id: 'cordis', trust: 'system' },
  ] })
  const result = await invoke(env, '创造模式')
  check('返回 success', result.kind === 'success', result.kind)
  check('切到 cordis', env.calls.select[0]?.id === 'cordis', env.calls.select[0]?.id)
  check('文案含创造模式', result.text.includes('创造模式'), result.text)
}

console.log('\n场景 5：`/preset 不存在的名字` → 报错且不调 select')
{
  const env = makeEnv()
  const result = await invoke(env, 'nope')
  check('返回 error', result.kind === 'error', result.kind)
  check('提示列出可用项', result.text.includes('standard') && result.text.includes('team'), result.text)
  check('没有调用 select', env.calls.select.length === 0)
}

console.log('\n场景 6：`/preset broken-one` → 拒绝不可用预设')
{
  const env = makeEnv()
  const result = await invoke(env, 'broken-one')
  check('返回 error', result.kind === 'error', result.kind)
  check('给出不可用原因', result.text.includes('加载失败'), result.text)
  check('没有调用 select', env.calls.select.length === 0)
}

console.log('\n场景 7：宿主拒绝（locked）→ 错误被翻译成文案')
{
  const env = makeEnv({ selectThrows: true })
  const result = await invoke(env, 'team')
  check('返回 error', result.kind === 'error', result.kind)
  check('文案含锁定原因', result.text.includes('already started'), result.text)
}

console.log('\n场景 8：取不到 live Agent 时回退到命令自带的 agent')
{
  const env = makeEnv({ noAgents: true })
  const result = await invoke(env, 'team')
  // 命令给的 agent 只有 id，没有 ctx/session → 应被拒绝，而不是崩掉。
  check('返回 error 而不是抛异常', result.kind === 'error', result.kind)
  check('说明找不到 Agent', result.text.includes('找不到'), result.text)
}

console.log('\n场景 9：取不到 live Agent，但命令给了完整 agent → 仍可切换')
{
  const env = makeEnv({ noAgents: true })
  const fullAgent = { id: 'sess-1', ctx: { marker: 'agent-ctx' }, session: { append() {} } }
  const result = await invoke(env, 'team', fullAgent)
  check('返回 success', result.kind === 'success', result.kind)
  check('调用了 select', env.calls.select.length === 1)
}

console.log('\n场景 10：前后空格被裁掉')
{
  const env = makeEnv()
  const result = await invoke(env, '  team  ')
  check('返回 success', result.kind === 'success', result.kind)
  check('id 无空格', env.calls.select[0]?.id === 'team', env.calls.select[0]?.id)
}

console.log(`\n${'='.repeat(50)}`)
console.log(`结果：${pass} 通过，${fail} 失败`)
process.exit(fail === 0 ? 0 : 1)
