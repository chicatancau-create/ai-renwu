// 真实加载 memsearch 客户端模块，用假 window/document 捕获它注入的 <style> 文本。
// 这样验证的是「运行时真正生效的那串 CSS」，而不是靠正则去猜源码。
import { readFileSync } from 'node:fs'

const FILE = 'C:/Users/Admin/.dsh/profiles/desktop/node_modules/@zilliz/memsearch-dsh/client.js'
const code = readFileSync(FILE, 'utf8')

// ---- 假 DOM ----
const styles = []
const fakeElement = () => ({
  id: '',
  dataset: {},
  setAttribute() {},
  appendChild() {},
  remove() {},
  textContent: '',
})
globalThis.document = {
  head: { appendChild: (el) => styles.push(el) },
  body: { appendChild: (el) => styles.push(el) },
  createElement: () => fakeElement(),
  getElementById: (id) => styles.find((s) => s.id === id) ?? null,
  querySelector: () => null,
  addEventListener() {},
  removeEventListener() {},
}
globalThis.window = globalThis

// ---- 假 React ----
const ReactStub = {
  createElement: (type, props, ...children) => ({ type, props, children }),
  useState: (init) => [typeof init === 'function' ? init() : init, () => {}],
  useEffect: () => {},
  useCallback: (fn) => fn,
  useRef: (init) => ({ current: init }),
  useMemo: (fn) => fn(),
}

// ---- 捕获模块工厂 ----
let captured
globalThis.window.__ModuleLoader__ = {
  load: (def) => {
    captured = def
  },
}

await import('file:///' + FILE)
if (!captured) throw new Error('模块没有注册工厂')

const mod = captured.factory((name) => {
  if (name === 'react') return ReactStub
  throw new Error('未知依赖: ' + name)
})

console.log('导出键:', Object.keys(mod))
console.log('inject:', JSON.stringify(mod.inject))

// ---- 用假 ctx 触发 apply，收集注入的 CSS ----
const registered = []
const slots = {
  inject: (name, fn) => fn(),
  register: (meta, comp) => {
    registered.push({ meta, comp })
    return () => {}
  },
}
mod.apply({ get: (k) => (k === 'slots' ? slots : undefined) })

const css = styles.map((s) => s.textContent).join('\n')
console.log('注入的 style 元素数:', styles.length)
console.log('CSS 长度:', css.length, '字符')
console.log('注册的插槽:', JSON.stringify(registered.map((r) => r.meta)))

const rules = css.split('}').filter((r) => r.trim() !== '')
const show = ['.msr-root', '.msr-root.msr-collapsed .msr-capsule', '.msr-capsule', '.msr-capsule-dot']
console.log('\n=== 关键规则 ===')
for (const w of show) {
  const hit = rules.find((r) => r.trim().replace(/^\s+/, '').startsWith(w + '{'))
  console.log(hit ? '  ' + hit.trim() + '}' : '  缺失: ' + w)
}

const problems = []
if (!/\.msr-root\{[^}]*display:flex/.test(css)) problems.push('.msr-root 未设置 flex')
if (!/\.msr-root\{[^}]*width:100%/.test(css)) problems.push('.msr-root 未撑满')
if (!css.includes('.msr-root.msr-collapsed .msr-capsule{position:fixed')) problems.push('收起态没有脱离文档流（缺少 position:fixed）')
if (!css.includes('left:25.1vw')) problems.push('收起态缺少水平兜底值')
if (!css.includes('transform:translate(-50%,-50%)')) problems.push('收起态缺少自居中 transform')
if (typeof mod.__pinToViewport !== 'function') problems.push('缺少 pinToViewport 测试钩子（运行时定位会失效）')
if (!css.includes('border:1px solid var(--msr-border)')) problems.push('胶囊边框被弄丢，会变成一块没有轮廓的色斑')
if ((css.match(/\{/g) ?? []).length !== (css.match(/\}/g) ?? []).length) problems.push('花括号不配平')

// 界面开关必须和插槽注册一致：关掉开关就一个插槽都不该注册（等于界面上彻底没有它）。
if (typeof mod.__showSkillDock !== 'boolean') {
  problems.push('缺少 __showSkillDock 开关导出')
} else if (mod.__showSkillDock === false) {
  if (registered.length !== 0) problems.push('开关为 false，但仍然注册了插槽（界面上还会冒出来）')
} else {
  if (registered.length !== 1) problems.push('开关为 true，但插槽注册数量异常')
  if (registered[0]?.meta?.name !== 'conversation.input.dock') problems.push('插槽名变了')
}

console.log('\n界面开关 SHOW_SKILL_DOCK =', mod.__showSkillDock)
console.log('\n' + '='.repeat(52))
if (problems.length === 0) {
  console.log('结果：CSS 齐备，开关状态与插槽注册一致（' + (mod.__showSkillDock ? '显示' : '已隐藏，界面上不出现') + '）')
} else {
  console.log('结果：发现问题')
  for (const p of problems) console.log('  - ' + p)
  process.exitCode = 1
}
