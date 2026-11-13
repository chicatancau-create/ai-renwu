// 验证清理通道：ctx.effect 优先，缺失时退化到 ctx.on('disposed'|'dispose')。
//
// 真实环境日志显示 `ctx.effect 不可用`，所以退化路径必须确实有效，
// 否则「禁用插件」就永远无法还原补丁——回滚能力等于不存在。
import { apply } from 'file:///C:/Users/Admin/.dsh/profiles/desktop/node_modules/dsh-preset-unlock/index.js'

const results = []
const check = (name, ok, detail) => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`)
}

function makeKernelClass() {
  return class Kernel {
    constructor() {
      this.switches = new Map()
      this.recomposed = []
    }
    async select(agent, agentPreset) {
      const boundary = this.boundary
      if (boundary.openTurnStartSeq !== null || boundary.lastTurn > 0) {
        const error = new Error('This session has already started')
        error.code = 'agent-preset/locked'
        throw error
      }
      return agentPreset
    }
    async recompose(ctx, id) {
      this.recomposed.push(id)
      return { id }
    }
  }
}

function makeAgent() {
  return { id: 'session-cleanup', ctx: { id: 'c' }, session: { append: () => {} } }
}

/** 构造一个只带指定清理通道的 ctx，模拟真实加载器给出的受限 ctx。 */
function makeCtx(registry, { withEffect = false, withOn = false } = {}) {
  const effects = []
  const listeners = new Map()
  const ctx = {
    agentPresets: registry,
    logger: { warn: () => {} },
  }
  if (withEffect) {
    ctx.effect = (fn, label) => {
      effects.push({ fn, label })
      return () => {}
    }
  }
  if (withOn) {
    ctx.on = (event, fn) => {
      if (!listeners.has(event)) listeners.set(event, [])
      listeners.get(event).push(fn)
    }
  }
  return { ctx, effects, listeners }
}

function mount(registry, opts) {
  registry.owner = {
    sessionProjections: { stateOf: () => ({ openTurnStartSeq: null, lastTurn: 1 }) },
  }
  const made = makeCtx(registry, opts)
  apply(made.ctx)
  return made
}

// ---- 通道 1：有 ctx.effect 时用它 ----
{
  const kernel = new (makeKernelClass())()
  kernel.boundary = { openTurnStartSeq: null, lastTurn: 1 }
  const proto = Object.getPrototypeOf(kernel)
  const original = proto.select
  const { effects } = mount(kernel, { withEffect: true, withOn: true })

  check('有 effect 时注册了 effect', effects.length === 1, `effects=${effects.length}`)
  const dispose = effects[0].fn()
  check('effect 工厂返回 dispose', typeof dispose === 'function', typeof dispose)
  dispose()
  check('effect 通道还原成功', proto.select === original, proto.select === original ? 'identity match' : 'MISMATCH')
}

// ---- 通道 2：没有 ctx.effect，只有 ctx.on ----
{
  const kernel = new (makeKernelClass())()
  kernel.boundary = { openTurnStartSeq: null, lastTurn: 1 }
  const proto = Object.getPrototypeOf(kernel)
  const original = proto.select
  const { effects, listeners } = mount(kernel, { withEffect: false, withOn: true })

  check('无 effect 时没有 effect 注册', effects.length === 0, `effects=${effects.length}`)
  check('已退化到 ctx.on 注册', listeners.size >= 1, `事件=[${[...listeners.keys()].join(',')}]`)
  check('注册了 disposed 事件', listeners.has('disposed'), `has=${listeners.has('disposed')}`)

  // 触发 disposed：应还原
  const handlers = listeners.get('disposed') ?? []
  handlers.forEach((fn) => fn())
  check('ctx.on 通道还原成功', proto.select === original, proto.select === original ? 'identity match' : 'MISMATCH')
}

// ---- 通道 3：两条都没有，必须不崩溃且功能仍然可用 ----
{
  const kernel = new (makeKernelClass())()
  kernel.boundary = { openTurnStartSeq: null, lastTurn: 1 }
  const proto = Object.getPrototypeOf(kernel)
  let threw = false
  try {
    mount(kernel, { withEffect: false, withOn: false })
  } catch {
    threw = true
  }
  check('无任何清理通道时不崩溃', threw === false, `threw=${threw}`)
  check('无清理通道时补丁仍生效', proto.select.name === 'selectUnlocked', proto.select.name)

  // 功能仍应可用
  const agent = makeAgent()
  const outcome = await kernel.select(agent, 'preset-x').then(
    (v) => ({ ok: true, v }),
    (e) => ({ ok: false, e }),
  )
  check('无清理通道时功能仍可用', outcome.ok === true && outcome.v === 'preset-x', JSON.stringify(outcome.ok))
}

const failed = results.filter((r) => !r.ok).length
console.log('\n' + '='.repeat(52))
console.log(`结果：${results.length - failed} 通过，${failed} 失败`)
process.exit(failed === 0 ? 0 : 1)
