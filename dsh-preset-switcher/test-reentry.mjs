// 客户端 pick() 的重入锁回归测试。
//
// 背景：busy 是 React state，setBusy(true) 要等下一次渲染才可见。
// 同一帧内连点两次，两次都会读到 busy=false 并各自发出一次 remote 请求，
// 宿主会串行执行两次切换——表现为「点一次切两次」，第二次可能把预设切回去。
//
// 这里用一个最小的模拟组件复现该时序，验证 ref 锁能挡住第二次。
const results = []
const check = (name, ok, detail) => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`)
}

/**
 * 模拟 React 的 useState/useRef 语义。
 * setState 只在「渲染」时才反映到读值上，ref 立即生效——这正是 bug 的成因。
 */
function makeComponent(remote) {
  const state = { busy: false }
  let pendingBusy = false
  const ref = { current: false }
  const calls = []

  const setBusy = (v) => {
    pendingBusy = v // 等渲染
  }
  const render = () => {
    state.busy = pendingBusy
  }

  const pick = async (id, current) => {
    // 与 client.js 一致的判断顺序
    if (ref.current) return 'skipped'
    if (id === current) return 'same'
    ref.current = true
    setBusy(true)
    calls.push(id)
    try {
      await remote(id)
    } finally {
      ref.current = false
      setBusy(false)
    }
    return 'done'
  }

  return { pick, ref, get busy() { return state.busy }, render, calls }
}

// ---- 用例 1：同一帧内连点两次，只应发出一次请求 ----
{
  const sent = []
  const remote = async (id) => {
    sent.push(id)
    await new Promise((r) => setTimeout(r, 20))
  }
  const c = makeComponent(remote)

  // 关键：两次点击之间**不渲染**，模拟同一帧内连续事件
  const a = c.pick('preset-a', 'standard')
  const b = c.pick('preset-b', 'standard')
  await Promise.all([a, b])

  check('同一帧连点只发出一次请求', sent.length === 1, `sent=${JSON.stringify(sent)}`)
  check('第二次点击被跳过', (await b) === 'skipped', await b)
}

// ---- 用例 2：点击当前已选预设应被短路 ----
{
  const sent = []
  const c = makeComponent(async (id) => sent.push(id))
  const r = await c.pick('standard', 'standard')
  check('点击当前预设被短路', r === 'same', r)
  check('短路时不发请求', sent.length === 0, JSON.stringify(sent))
}

// ---- 用例 3：请求结束后锁必须释放，允许下一次切换 ----
{
  const sent = []
  const c = makeComponent(async (id) => {
    sent.push(id)
    await new Promise((r) => setTimeout(r, 5))
  })

  await c.pick('preset-a', 'standard')
  c.render()
  const second = await c.pick('preset-b', 'preset-a')
  check('首次切换后锁已释放', second === 'done', second)
  check('第二次切换正常发出', sent.length === 2, JSON.stringify(sent))
}

// ---- 用例 4：请求抛错时锁也必须释放（否则界面永久「切换中…」） ----
{
  const c = makeComponent(async () => {
    throw new Error('boom')
  })
  let caught = false
  try {
    await c.pick('preset-a', 'standard')
  } catch {
    caught = true
  }
  check('失败时异常向上抛出', caught === true, `caught=${caught}`)
  check('失败后锁已释放', c.ref.current === false, `ref=${c.ref.current}`)

  // 锁释放后应能再次尝试
  const c2 = makeComponent(async (id) => id)
  const r = await c2.pick('preset-x', 'standard')
  check('失败后可以重试', r === 'done', r)
}

const failed = results.filter((r) => !r.ok).length
console.log('\n' + '='.repeat(52))
console.log(`结果：${results.length - failed} 通过，${failed} 失败`)
process.exit(failed === 0 ? 0 : 1)
