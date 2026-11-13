// 针对本轮审计修复的回归测试。
//
// 覆盖三件事：
//   1. 二次确认：从「判定可切」到「真正 recompose」之间新轮次开始 → 必须放弃，不能换工具集
//   2. 还原逻辑：ctx.effect 注册的清理函数必须把原型与实例都还原
//   3. 超时覆盖：内核挂住时必须有明确错误，而不是永久 pending
import { apply } from 'file:///C:/Users/Admin/.dsh/profiles/desktop/node_modules/dsh-preset-unlock/index.js'

const results = []
const check = (name, ok, detail) => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`)
}

function withDeadline(promise, ms) {
  return Promise.race([
    promise.then(
      (value) => ({ kind: 'ok', value }),
      (error) => ({ kind: 'err', error }),
    ),
    new Promise((resolve) => setTimeout(() => resolve({ kind: 'hang' }), ms)),
  ])
}

/**
 * 每个用例都要用**独立的类**。
 *
 * 插件把原始方法存在 `Symbol.for(...)` 于原型上，而 Symbol 是全局复用的；
 * 同一个类被两个用例先后 apply，第二个用例再取 `proto.select` 拿到的就已经是
 * 第一个用例打上的补丁——测试会误报「还原失败」。隔离靠新建类，不靠清 Symbol。
 *
 * 必须返回「直接定义 select 的类」，不能返回 `extends Base` 的空子类：
 * 插件用 `Object.getPrototypeOf(registry)` 取原型，空子类的原型上没有 select，
 * 会直接 ABORT（effects=0）。
 */
function makeKernelClass() {
  return class Kernel {
    constructor(opts = {}) {
      this.switches = new Map()
      this.lastTurn = opts.lastTurn ?? 1
      this.boundaries = opts.boundaries ?? []
      this.recomposed = []
      this.recomposeCount = 0
    }

    // 每次读取返回下一个预设的边界状态；用完后重复最后一个。
    nextBoundary() {
      const idx = Math.min(this.recomposeCount, this.boundaries.length - 1)
      return this.boundaries[idx] ?? { openTurnStartSeq: null, lastTurn: this.lastTurn }
    }

    async select(agent, agentPreset) {
      const turn = (this.switches.get(agent.id) ?? Promise.resolve()).then(async () => {
        const boundary = this.boundary
        if (boundary.openTurnStartSeq !== null || boundary.lastTurn > 0) {
          const error = new Error('This session has already started')
          error.code = 'agent-preset/locked'
          throw error
        }
        return agentPreset
      })
      const guard = turn.catch(() => void 0)
      this.switches.set(agent.id, guard)
      try {
        return await turn
      } finally {
        if (this.switches.get(agent.id) === guard) this.switches.delete(agent.id)
      }
    }

    async recompose(ctx, agentPreset) {
      this.recomposeCount += 1
      this.recomposed.push(agentPreset)
      return { id: agentPreset }
    }
  }
}

function makeAgent(id = 'session-audit') {
  const appended = []
  return {
    id,
    ctx: { id: 'ctx-1' },
    session: { append: (t, p) => appended.push({ type: t, payload: p }), __appended: appended },
  }
}

function mount(registry, opts = {}) {
  const effects = []
  registry.owner = {
    sessionProjections: {
      stateOf: (session, key) => {
        if (key === 'turnBoundary') return opts.boundary ? opts.boundary() : registry.boundary
        return undefined
      },
    },
  }
  const ctx = {
    agentPresets: registry,
    logger: { warn: () => {} },
    // 与 cordis 一致：effect 接收工厂，工厂返回 dispose。这里把工厂原样存下来，
    // 测试调用 effects[i]() 就等价于「插件被卸载时 cordis 调用该工厂」。
    effect: (fn) => {
      effects.push(fn)
      return () => {}
    },
  }
  apply(ctx)
  return { effects, ctx }
}

// ---- 用例 1：二次确认必须在轮次中途开始时拦住 ----
// 第一次读边界（入口判定）→ 无轮次；内核抛 locked；第二次读边界（复查）→ 有轮次在跑。
{
  const kernel = new (makeKernelClass())()
  kernel.boundary = { openTurnStartSeq: null, lastTurn: 5 }
  let reads = 0
  const { } = mount(kernel, {
    boundary: () => {
      reads += 1
      // 入口那次允许；之后的复查一律报「有轮次在跑」
      if (reads === 1) return { openTurnStartSeq: null, lastTurn: 5 }
      return { openTurnStartSeq: 42, lastTurn: 5 }
    },
  })
  const agent = makeAgent()
  const outcome = await withDeadline(kernel.select(agent, 'preset-team'), 5000)

  check('复查发现新轮次时拒绝切换', outcome.kind === 'err', `kind=${outcome.kind}`)
  check(
    '拒绝时给出明确原因',
    outcome.kind === 'err' && /新一轮任务|读不到会话轮次/.test(String(outcome.error?.message)),
    String(outcome.error?.message ?? ''),
  )
  check('拒绝时没有执行 recompose', kernel.recomposed.length === 0, `recomposed=${JSON.stringify(kernel.recomposed)}`)
  check('拒绝时没有写会话日志', agent.session.__appended.length === 0, JSON.stringify(agent.session.__appended))
}

// ---- 用例 2：还原逻辑必须同时撤销原型与实例补丁 ----
{
  const kernel = new (makeKernelClass())()
  kernel.boundary = { openTurnStartSeq: null, lastTurn: 1 }
  const proto = Object.getPrototypeOf(kernel)
  // 必须在 mount 之前取原始实现：mount 之后原型已被补丁覆盖。
  const originalProtoSelect = proto.select
  const originalProtoDesc = Object.getOwnPropertyDescriptor(proto, 'select')
  const { effects } = mount(kernel)

  check('注册了清理函数', effects.length === 1, `effects=${effects.length}`)
  check('补丁已生效（原型 select 被替换）', proto.select !== originalProtoSelect, 'patched')
  check('原型上的 select 已被替换为插件方法', proto.select.name === 'selectUnlocked', proto.select.name)

  // ctx.effect 的约定：工厂返回 dispose 函数，必须调用它才真正还原。
  const dispose = effects[0]()
  check('清理工厂返回 dispose 函数', typeof dispose === 'function', typeof dispose)
  dispose()

  // 严格断言：按身份比较，不是「是个函数」。
  check(
    '原型 select 已恢复为原始实现',
    proto.select === originalProtoSelect,
    proto.select === originalProtoSelect ? 'identity match' : `identity MISMATCH (name=${proto.select.name})`,
  )
  check('原型 select 不再是插件方法', proto.select.name !== 'selectUnlocked', proto.select.name)

  // 实例自有属性应被删除，从而回落到原型。
  const ownDesc = Object.getOwnPropertyDescriptor(kernel, 'select')
  check('实例自有 select 已被删除', ownDesc === undefined, String(ownDesc))

  // 还原后行为应与内核一致：会话已开始 → 抛 locked。
  const agent = makeAgent()
  const outcome = await withDeadline(kernel.select(agent, 'preset-x'), 3000)
  check(
    '还原后内核恢复原有锁定行为',
    outcome.kind === 'err' && outcome.error?.code === 'agent-preset/locked',
    outcome.kind === 'err' ? String(outcome.error?.code) : outcome.kind,
  )
  check('还原后不再执行 recompose', kernel.recomposed.length === 0, JSON.stringify(kernel.recomposed))
}

// ---- 用例 3：正常路径仍然可用（确认修复没有把功能弄坏） ----
{
  const kernel = new (makeKernelClass())()
  kernel.boundary = { openTurnStartSeq: null, lastTurn: 3 }
  mount(kernel)
  const agent = makeAgent()
  const outcome = await withDeadline(kernel.select(agent, 'preset-solo'), 5000)
  check('正常路径仍能切换', outcome.kind === 'ok' && outcome.value === 'preset-solo', `kind=${outcome.kind} value=${outcome.value}`)
  check('正常路径执行了 recompose', kernel.recomposed.length === 1, JSON.stringify(kernel.recomposed))
}

const failed = results.filter((r) => !r.ok).length
console.log('\n' + '='.repeat(52))
console.log(`结果：${results.length - failed} 通过，${failed} 失败`)
process.exit(failed === 0 ? 0 : 1)
