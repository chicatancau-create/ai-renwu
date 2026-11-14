// 复现并验证「自己等自己」的死锁是否已修复。
//
// 死锁成因：内核 select 第一件事是
//   await (this.switches.get(agent.id) ?? Promise.resolve())
// 若插件把自己的 guard 留在 switches 里再去调内核，内核就会 await 这个尚未完成的任务，
// 形成「我等你、你等我」的环，表现为日志只有 ENTER、界面永远「切换中…」。
//
// 本测试用一个「内核语义与真身一致」的假内核来验证：
//   1. 假内核 select 会 await switches 上的链（复刻真内核行为）
//   2. 会话已开始（lastTurn > 0），因此内核会抛 agent-preset/locked
//   3. 插件应在 5 秒内完成切换，而不是永远挂住
import { apply } from 'file:///C:/Users/Admin/.dsh/profiles/desktop/node_modules/dsh-preset-unlock/index.js'

const results = []
const check = (name, ok, detail) => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`)
}

/** 假内核：select 的串行化语义与真内核一致（先 await switches 上的链）。 */
class KernelRegistry {
  constructor({ lastTurn = 1, openTurnStartSeq = null } = {}) {
    this.switches = new Map()
    this.boundary = { openTurnStartSeq, lastTurn }
    this.recomposed = []
  }

  async select(agent, agentPreset) {
    // ← 真内核就是这一行导致了死锁
    const turn = (this.switches.get(agent.id) ?? Promise.resolve()).then(async () => {
      const boundary = this.boundary
      if (boundary.openTurnStartSeq !== null || boundary.lastTurn > 0) {
        const error = new Error('This session has already started')
        error.code = 'agent-preset/locked'
        error.details = { sessionId: agent.id, agentPreset }
        throw error
      }
      return agentPreset
    })
    const guard = turn.catch(() => undefined)
    this.switches.set(agent.id, guard)
    try {
      return await turn
    } finally {
      if (this.switches.get(agent.id) === guard) this.switches.delete(agent.id)
    }
  }

  async recompose(ctx, agentPreset) {
    this.recomposed.push(agentPreset)
    return { id: agentPreset }
  }

  async list() {
    return { presets: [], authorable: true }
  }
}

function makeAgent(id = 'session-test') {
  const appended = []
  return {
    id,
    ctx: { id: 'ctx-1' },
    session: {
      append: (type, payload) => appended.push({ type, payload }),
      __appended: appended,
    },
  }
}

/** 挂载插件。owner.sessionProjections 提供 turnBoundary 投影。 */
function mount(registry) {
  registry.owner = {
    sessionProjections: {
      stateOf: (session, key) => {
        if (key === 'turnBoundary') return registry.boundary
        if (key === 'agentPreset') return undefined
        return undefined
      },
    },
  }
  apply({ agentPresets: registry, logger: { warn: () => {} } })
  return registry
}

/** 带超时地等待一个 Promise，用于检测「永久挂住」。 */
function withDeadline(promise, ms) {
  return Promise.race([
    promise.then(
      (value) => ({ kind: 'ok', value }),
      (error) => ({ kind: 'err', error }),
    ),
    new Promise((resolve) => setTimeout(() => resolve({ kind: 'hang' }), ms)),
  ])
}

// ---- 核心用例：会话已开始 + 内核串行化语义 → 必须能切过去，不能挂死 ----
{
  const kernel = new KernelRegistry({ lastTurn: 3, openTurnStartSeq: null })
  mount(kernel)
  const agent = makeAgent()

  const startedAt = Date.now()
  const outcome = await withDeadline(kernel.select(agent, 'preset-team'), 5000)
  const elapsed = Date.now() - startedAt

  check(
    '会话已开始时不挂死（5 秒内返回）',
    outcome.kind !== 'hang',
    outcome.kind === 'hang' ? `挂死超过 5000ms` : `elapsed=${elapsed}ms`,
  )
  check('成功切换到目标预设', outcome.kind === 'ok' && outcome.value === 'preset-team', `outcome=${outcome.kind === 'ok' ? outcome.value : outcome.kind}`)
  check('确实走了 recompose', kernel.recomposed.length === 1, `recomposed=${JSON.stringify(kernel.recomposed)}`)
  check(
    '会话日志记录预设变更',
    agent.session.__appended.some((e) => e.type === 'agent-preset/selected' && e.payload.agentPreset === 'preset-team'),
    JSON.stringify(agent.session.__appended),
  )
  check('切换后 switches 已清空（无残留链）', kernel.switches.size === 0, `size=${kernel.switches.size}`)
}

// ---- 连续快速切换：串行化必须仍然有效，且不能互相卡死 ----
{
  const kernel = new KernelRegistry({ lastTurn: 5, openTurnStartSeq: null })
  mount(kernel)
  const agent = makeAgent()

  const a = kernel.select(agent, 'preset-a')
  const b = kernel.select(agent, 'preset-b')
  const c = kernel.select(agent, 'preset-c')

  const outcome = await withDeadline(Promise.allSettled([a, b, c]), 8000)
  check('连续三次切换不挂死', outcome.kind !== 'hang', outcome.kind === 'hang' ? '挂死超过 8000ms' : 'ok')
  if (outcome.kind === 'ok') {
    const allOk = outcome.value.every((r) => r.status === 'fulfilled')
    check('三次切换全部成功', allOk, JSON.stringify(outcome.value.map((r) => r.status)))
  }
  check('最终 switches 无残留', kernel.switches.size === 0, `size=${kernel.switches.size}`)
}

// ---- 未开始的会话：内核应直接通过，不走 recompose ----
{
  const kernel = new KernelRegistry({ lastTurn: 0, openTurnStartSeq: null })
  mount(kernel)
  const agent = makeAgent()
  const outcome = await withDeadline(kernel.select(agent, 'preset-solo'), 5000)
  check('未开始的会话直接通过', outcome.kind === 'ok' && outcome.value === 'preset-solo', `outcome=${outcome.kind}`)
  check('未开始时未走 recompose', kernel.recomposed.length === 0, `recomposed=${kernel.recomposed.length}`)
}

// ---- 残留死链：内核 switches 里留着一条永远不会 settle 的链（v6 死锁的历史遗留） ----
// 真实现场就是这样：v6 死锁过一次，那条链永远挂着，之后每次点击都会被它拖死。
{
  const kernel = new KernelRegistry({ lastTurn: 3, openTurnStartSeq: null })
  mount(kernel)
  const agent = makeAgent()

  // 模拟历史死锁留下的死链：一个永不 resolve 的 Promise
  kernel.switches.set(agent.id, new Promise(() => {}))

  const startedAt = Date.now()
  const outcome = await withDeadline(kernel.select(agent, 'preset-team'), 5000)
  const elapsed = Date.now() - startedAt

  check(
    '内核里有残留死链时仍能切换',
    outcome.kind === 'ok',
    outcome.kind === 'hang' ? `挂死超过 5000ms` : `elapsed=${elapsed}ms value=${outcome.value}`,
  )
  check('残留死链已被清理', kernel.switches.size === 0, `size=${kernel.switches.size}`)
}

const failed = results.filter((r) => !r.ok).length
console.log('\n' + '='.repeat(52))
console.log(`结果：${results.length - failed} 通过，${failed} 失败`)
process.exit(failed === 0 ? 0 : 1)
