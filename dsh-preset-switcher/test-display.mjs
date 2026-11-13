/**
 * 离线验证 client.js 里的文案解析逻辑（displayText）。
 *
 * client.js 是浏览器模块，不能直接 import，所以这里把同一份映射与判定逻辑
 * 抽出来复制验证：只要这里的用例全绿，且与 client.js 源码保持一致，就说明
 * 内置预设会显示中文、自定义预设会显示作者自己的名字。
 *
 * 运行：node test-display.mjs
 */

import { readFileSync } from 'node:fs'

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

const source = readFileSync(new URL('./client.js', import.meta.url), 'utf8')

/** 与 client.js 内联的 BUILT_IN 表逐项比对，防止两边漂移。 */
const BUILT_IN = {
  standard: {
    name: '标准模式',
    description: '处理代码、文件和资料，适合大多数任务。Agent 会按需使用检索、编辑和终端等工具。',
  },
  ptc: {
    name: 'PTC 模式',
    description: '包含标准模式的所有能力，更适合批量调用工具，并对结果进行筛选、整理、去重、统计或汇总的任务。',
  },
  minimal: {
    name: '极简模式',
    description: 'Agent 使用终端和图片读取工具，并支持上下文压缩，适合测试和对比其基础表现。',
  },
  cordis: {
    name: '创造模式',
    description: '用对话定制 DSH：让 Agent 编写插件，添加新功能或界面；也能组合工具和提示词，创建自己的模式。',
  },
}

function displayText(preset) {
  const built = BUILT_IN[preset.id]
  const shipped =
    built !== undefined &&
    (preset.trust === 'system' || preset.name === undefined || preset.name === preset.id)
  if (shipped) return built
  return { name: preset.name ?? preset.id, description: preset.description }
}

console.log('场景 1：client.js 源码确实内联了四个内置预设的中文名')
{
  for (const [id, copy] of Object.entries(BUILT_IN)) {
    check(`${id} → ${copy.name}`, source.includes(`name: '${copy.name}'`), '源码里找不到该名字')
  }
}

console.log('\n场景 2：菜单复用出厂浮层配色（保证背景色与系统浮层一致）')
{
  check('触发按钮用了出厂 seat 类', source.includes('m2hUqa_seat'))
  check('浮层底色用出厂实测色', source.includes('#2C2E34'))
  check('按明暗模式区分浮层底色', source.includes('prefersDark'))
  check('浅色主题下用白底', source.includes("'#FFFFFF'"))
  check('不再依赖 body 作用域上会跑偏的令牌', !source.includes('readToken'))
  check('菜单用 fixed 定位避开页头 overflow 裁剪', source.includes("position: 'fixed'"))
  check('菜单层级压过页面内容', source.includes('zIndex: 2147483000'))
}

console.log('\n场景 2b：菜单一定可见（裁剪与定位安全）')
{
  check('require react-dom 包在 try 里', /try\s*\{[^}]*require\('react-dom'\)/.test(source))
  check('有 catch 兜底', source.includes('react-dom 不可用'))
  check('优先 portal 到 body', source.includes('createPortal(menuBody, document.body)'))
  check('portal 不可用时仍渲染菜单', source.includes(': menuBody'))
  check('图标缺失时用内联 SVG', source.includes('IconAgentPreset === undefined'))
  check('有贴边与上翻逻辑', source.includes('roomBelow') && source.includes('style.bottom'))
}

console.log('\n场景 3：内置预设（trust=system, 无 name）→ 中文')
{
  for (const [id, copy] of Object.entries(BUILT_IN)) {
    const text = displayText({ id, trust: 'system' })
    check(`${id} 显示「${copy.name}」`, text.name === copy.name, text.name)
    check(`${id} 有中文描述`, text.description === copy.description)
  }
}

console.log('\n场景 4：内置预设带 name 等于 id（宿主回退形态）→ 仍用中文')
{
  const text = displayText({ id: 'cordis', trust: 'system', name: 'cordis' })
  check('cordis 显示「创造模式」', text.name === '创造模式', text.name)
}

console.log('\n场景 5：自定义预设 → 用作者自己的名字，不翻译')
{
  const text = displayText({ id: 'solo', name: '单人交付', description: '一个智能体独立完成。' })
  check('保留自定义名', text.name === '单人交付', text.name)
  check('保留自定义描述', text.description === '一个智能体独立完成。')
}

console.log('\n场景 6：自定义预设没有名字 → 回退到 id')
{
  const text = displayText({ id: 'my-custom' })
  check('回退到 id', text.name === 'my-custom', text.name)
  check('描述为 undefined', text.description === undefined)
}

console.log('\n场景 7：自定义预设故意用了内置 id 但带自己的名字 → 尊重作者')
{
  const text = displayText({ id: 'standard', name: '我的标准', description: '自定义描述' })
  check('不被内置文案覆盖', text.name === '我的标准', text.name)
}

console.log('\n场景 8：四个 super-agent 中文预设原样显示')
{
  const zh = JSON.parse(readFileSync('C:/Users/Admin/.dsh/profiles/desktop/super-agent-sync/zh.json', 'utf8'))
  for (const key of ['solo', 'team', 'research', 'optimization']) {
    const text = displayText({ id: key, name: zh[key].name, description: zh[key].description })
    check(`${key} → ${zh[key].name}`, text.name === zh[key].name, text.name)
  }
}

console.log(`\n${'='.repeat(50)}`)
console.log(`结果：${pass} 通过，${fail} 失败`)
process.exit(fail === 0 ? 0 : 1)
