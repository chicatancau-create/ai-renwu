// 校验 memsearch 客户端里「视口坐标 → position:fixed 包含块坐标」的换算。
// 背景：dock 槽位祖先链里有 transform，fixed 元素的包含块不是视口，还会跟着滚，
// 所以落点必须运行时测量。这里用假 DOM 验证公式在各种祖先形态下都成立。
import { readFileSync } from 'node:fs'

const FILE = 'C:/Users/Admin/.dsh/profiles/desktop/node_modules/@zilliz/memsearch-dsh/client.js'
readFileSync(FILE, 'utf8')

globalThis.window = globalThis

const html = { __style: {}, parentElement: null, style: {} }
globalThis.document = { documentElement: html, addEventListener() {}, removeEventListener() {} }
globalThis.addEventListener = () => {}
globalThis.removeEventListener = () => {}
globalThis.getComputedStyle = (el) => (el && el.__style) || {}

let captured
globalThis.window.__ModuleLoader__ = { load: (d) => { captured = d } }

await import('file:///' + FILE)
if (!captured) throw new Error('模块没有注册工厂')

const ReactStub = {
  createElement: () => ({}),
  useState: (init) => [typeof init === 'function' ? init() : init, () => {}],
  useEffect: () => {},
  useCallback: (fn) => fn,
  useRef: (init) => ({ current: init }),
  useMemo: (fn) => fn(),
}
const mod = captured.factory((name) => {
  if (name === 'react') return ReactStub
  throw new Error('未知依赖: ' + name)
})

const pin = mod.__pinToViewport
let pass = 0
let fail = 0
function check(name, actual, expected) {
  if (actual === expected) {
    pass++
    console.log('  ✓ ' + name)
  } else {
    fail++
    console.log('  ✗ ' + name + ' — 期望 ' + JSON.stringify(expected) + '，实际 ' + JSON.stringify(actual))
  }
}

function el(opts = {}) {
  const o = {
    __style: opts.style || {},
    parentElement: opts.parent === undefined ? html : opts.parent,
    style: {},
    scrollLeft: opts.scrollLeft || 0,
    scrollTop: opts.scrollTop || 0,
    getBoundingClientRect: () => opts.rect || { left: 0, top: 0, right: 0, bottom: 0 },
  }
  return o
}

const VX = 473
const VY = 630

// 1. 祖先链里没有任何会创建包含块的属性 → 坐标就是视口坐标
{
  const p = el({ parent: html })
  const node = el({ parent: p })
  pin(node, VX, VY)
  check('普通祖先：left 等于视口坐标', node.style.left, VX + 'px')
  check('普通祖先：top 等于视口坐标', node.style.top, VY + 'px')
}

// 2. 祖先有 transform（最常见）→ 换算出包含块坐标，且滚回原视口位置
{
  const block = el({ style: { transform: 'translateZ(0)' }, rect: { left: 290, top: 40 }, scrollTop: 624 })
  const node = el({ parent: block })
  pin(node, VX, VY)
  const ox = 290 - 0
  const oy = 40 - 624
  check('transform 祖先：left 反解正确', node.style.left, Math.round(VX - ox) + 'px')
  check('transform 祖先：top 反解正确', node.style.top, Math.round(VY - oy) + 'px')
  const renderedY = oy + parseFloat(node.style.top)
  const renderedX = ox + parseFloat(node.style.left)
  check('transform 祖先：还原后确实落在视口目标 Y', Math.round(renderedY), VY)
  check('transform 祖先：还原后确实落在视口目标 X', Math.round(renderedX), VX)
}

// 3. 祖先只有 will-change: transform 也算包含块
{
  const block = el({ style: { willChange: 'transform' }, rect: { left: 100, top: 10 } })
  const node = el({ parent: block })
  pin(node, VX, VY)
  check('will-change:transform 祖先被识别', node.style.left, Math.round(VX - 100) + 'px')
}

// 4. contain: paint 也算包含块
{
  const block = el({ style: { contain: 'paint' }, rect: { left: 50, top: 0 } })
  const node = el({ parent: block })
  pin(node, VX, VY)
  check('contain:paint 祖先被识别', node.style.left, Math.round(VX - 50) + 'px')
}

// 5. 只认最近的包含块祖先，外层的不参与
{
  const outer = el({ style: { transform: 'scale(1)' }, rect: { left: 999, top: 999 } })
  const inner = el({ style: { filter: 'blur(0px)' }, rect: { left: 10, top: 20 }, parent: outer })
  const node = el({ parent: inner })
  pin(node, VX, VY)
  check('取最近包含块（内层 filter）', node.style.left, Math.round(VX - 10) + 'px')
  check('取最近包含块（内层 filter）Y', node.style.top, Math.round(VY - 20) + 'px')
}

// 6. 横向滚动也要抵消
{
  const block = el({ style: { transform: 'none' }, rect: { left: 0, top: 0 }, scrollLeft: 0 })
  const scroller = el({ style: { perspective: '1000px' }, rect: { left: 0, top: 0 }, scrollLeft: 120 })
  const node = el({ parent: scroller })
  pin(node, VX, VY)
  check('横向滚动被抵消', node.style.left, Math.round(VX + 120) + 'px')
  void block
}

// 7. 防御：节点或 style 缺失时不抛
{
  let threw = false
  try {
    pin(null, VX, VY)
    pin({}, VX, VY)
  } catch (e) {
    threw = true
  }
  check('空节点/无 style 不抛错', threw, false)
}

console.log('\n' + '='.repeat(52))
console.log('合计 ' + (pass + fail) + ' 项：' + pass + ' 通过，' + fail + ' 失败')
if (fail > 0) process.exitCode = 1
