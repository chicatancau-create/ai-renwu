// 验证 preset-unlock 的轮次判定与等待逻辑。
// 用假的 agentPresets 注册表把插件跑起来，检查四种情形：
//   1. 无轮次在跑 → 直接走内核，成功
//   2. 有轮次在跑 → 不立即拒绝，而是等轮次结束后再切
//   3. 读不到轮次状态 → 交回内核拒绝（安全兜底）
//   4. 非锁定错误 → 原样抛出，不吞异常
import { apply } from 'file:///C:/Users/Admin/.dsh/profiles/desktop/node_modules/dsh-preset-unlock/index.js'

const results = []
const check = (name, ok, detail) => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`)
}

/**
 * 造一个假的注册表。
 * @param boundary      stateOf('turnBoundary') 的返回值（null 表示读不到）
 * @param sessionStarted 内核自己判断的「会话已开始」，决定是否抛 locked
 */
function makeRegistry({ boundary, sessionStarted }) {
  const calls = { recompose: [] }
  const state = { boundary }

  class FakeRegistry {
    constructor() {
      this.switches = new Map()
    }

    async select(agent, agentPreset) {
      // 内核自己的边界判断独立于 stateOf：真实内核读的是自己的投影。
      if (sessionStarted) {
        const error = new Error('session has already started; its agent preset is fixed')
        error.code = 'agent-preset/locked'
        error.details = { sessionId: 'session-test' }
        throw error
      }
      return agentPreset
    }

    async recompose(ctx, agentPreset) {
      calls.recompose.push(agentPreset)
      return { id: agentPreset }
    }

    async list() {
      return { presets: [], authorable: true }
    }
  }

  const registry = new FakeRegistry()
  registry.owner = {
    sessionProjections: {
      stateOf: (session, key) => {
        if (key !== 'turnBoundary') return undefined
        return state.boundary
      },
    },
  }
  return { registry, calls, state }
}

function makeAgent() {
  const appended = []
  return {
    id: 'agent-1',
    ctx: { id: 'ctx-1' },
    session: {
      append: (type, payload) => appended.push({ type, payload }),
      __appended: appended,
    },
  }
}

/** 把插件挂到假注册表上。logger 故意只给 warn，顺带验证日志兜底。 */
function mount(registry) {
  apply({ agentPresets: registry, logger: { warn: () => {} } })
  return registry
}

// ---- 情形 1：无轮次在跑，会话未开始 ----
{
  const { registry, calls } = makeRegistry({
    boundary: { openTurnStartSeq: null, lastTurn: 0 },
    sessionStarted: false,
  })
  mount(registry)
  const agent = makeAgent()
  let value
  let error
  try {
    value = await registry.select(agent, 'preset-team')
  } catch (e) {
    error = e
  }
  check('无轮次时切换成功', error === undefined && value === 'preset-team', `value=${value} err=${error?.code}`)
  check('无轮次时未走 recompose', calls.recompose.length === 0, `recompose=${calls.recompose.length}`)
}

// ---- 情形 2：有轮次在跑，800ms 后结束 ----
{
  const { registry, calls, state } = makeRegistry({
    boundary: { openTurnStartSeq: 1, lastTurn: 2 },
    sessionStarted: true,
  })
  mount(registry)
  const agent = makeAgent()

  setTimeout(() => {
    state.boundary = { openTurnStartSeq: null, lastTurn: 3 }
  }, 800)

  const startedAt = Date.now()
  let value
  let error
  try {
    value = await registry.select(agent, 'preset-research')
  } catch (e) {
    error = e
  }
  const waited = Date.now() - startedAt

  check('有轮次时等待而非立即失败', error === undefined, `err=${error?.code ?? 'none'}`)
  check('等待后切换成功', value === 'preset-research', `value=${value}`)
  check('确实等了（>=700ms）', waited >= 700, `waited=${waited}ms`)
  check('改走 recompose 完成切换', calls.recompose.length === 1, `recompose=${calls.recompose.length}`)
  check(
    '会话日志记录预设变更',
    agent.session.__appended.some(
      (e) => e.type === 'agent-preset/selected' && e.payload.agentPreset === 'preset-research',
    ),
    JSON.stringify(agent.session.__appended),
  )
}

// ---- 情形 3：读不到轮次状态 → 交回内核拒绝 ----
{
  const { registry, calls } = makeRegistry({ boundary: null, sessionStarted: true })
  mount(registry)
  const agent = makeAgent()
  let error
  try {
    await registry.select(agent, 'preset-solo')
  } catch (e) {
    error = e
  }
  check('读不到状态时交回内核拒绝', error?.code === 'agent-preset/locked', `err=${error?.code}`)
  check('读不到状态时未走 recompose', calls.recompose.length === 0, `recompose=${calls.recompose.length}`)
}

// ---- 情形 4：非锁定错误必须原样抛出 ----
{
  const calls = { recompose: 0 }
  class ThrowingRegistry {
    constructor() {
      this.switches = new Map()
    }

    async select() {
      const error = new Error('preset 不存在')
      error.code = 'agent-preset/not-found'
      throw error
    }

    async recompose() {
      calls.recompose += 1
      return { id: 'x' }
    }

    async list() {
      return { presets: [], authorable: true }
    }
  }
  const registry = new ThrowingRegistry()
  registry.owner = {
    sessionProjections: { stateOf: () => ({ openTurnStartSeq: null, lastTurn: 1 }) },
  }
  mount(registry)
  const agent = makeAgent()
  let error
  try {
    await registry.select(agent, 'preset-nope')
  } catch (e) {
    error = e
  }
  check('其它错误原样抛出', error?.code === 'agent-preset/not-found', `err=${error?.code}`)
  check('其它错误未触发 recompose', calls.recompose === 0, `recompose=${calls.recompose}`)
}

const failed = results.filter((r) => !r.ok).length
console.log('\n' + '='.repeat(50))
console.log(`结果：${results.length - failed} 通过，${failed} 失败`)
process.exit(failed === 0 ? 0 : 1)
