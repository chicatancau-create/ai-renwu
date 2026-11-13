/**
 * 客户端：把会话标题栏那个只读的预设标签，换成一个真正能点的切换器。
 *
 * 三个必须绕开的出厂限制：
 *  1. 出厂 AgentPresetLabel 是纯 <span>，没有任何点击行为。
 *  2. 出厂 AgentPresetSeatController.apply() 里有 `if (!session.blank) return UNCHANGED`，
 *     会在浏览器端把切换请求直接丢弃，连远程调用都不会发出。所以这里自己调 remote。
 *  3. 页头容器有 overflow 裁剪，普通 position:absolute 的菜单会被裁掉看不见。
 *     因此菜单用 createPortal 挂到 document.body，并以 fixed 定位贴住按钮。
 *
 * 背景色：直接使用主题令牌 --dsw-alias-bg-overlay（"Overlay and popover background"），
 * 与出厂浮层用的是同一个令牌，颜色必然一致。
 *
 * 宿主端的 agent-preset/locked 硬锁由 dsh-preset-unlock 负责放开。
 */
window.__ModuleLoader__.load({
  id: '@local/dsh-preset-switcher',
  factory(require) {
    const React = require('react')
    const h = React.createElement

    /** 出厂 primitives 提供图标；拿不到就退回内联 SVG。 */
    let primitives
    try {
      primitives = require('@deepseek-ai/dsh-client-ui-primitives')
    } catch (cause) {
      console.warn('preset-switcher: 出厂 primitives 不可用，使用内联图标', cause)
      primitives = undefined
    }
    const IconAgentPreset = primitives?.IconAgentPresetOutlineRegular
    const IconChevronDown = primitives?.IconChevronDownOutlineRegular

    /** react-dom 提供 createPortal；拿不到就退回同树 fixed 定位（fixed 不受 overflow 裁剪）。 */
    let createPortal
    try {
      const ReactDOM = require('react-dom')
      createPortal = ReactDOM?.createPortal
    } catch (cause) {
      console.warn('preset-switcher: react-dom 不可用，菜单改用同树 fixed 定位', cause)
      createPortal = undefined
    }

    /**
     * 出厂 AgentPresetSeat.module.css 的类名。
     * 那张样式表由 @deepseek-ai/dsh-client-ui-agent-preset 注入到页面，直接复用即可。
     */
    const CSS = {
      seat: 'm2hUqa_seat',
      seatIcon: 'm2hUqa_seatIcon',
      seatLabel: 'm2hUqa_seatLabel',
      chevron: 'm2hUqa_chevron',
    }

    /**
     * 出厂内置预设没有 name 字段，文案来自 locale 字典。
     * 这里照抄 @deepseek-ai/dsh-agent-presets 的 display.js 映射表，写成中文。
     */
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

    /**
     * 解析一条预设的显示文案，与出厂 presetDisplayText 同语义：
     * 内置预设走中文映射，自定义预设用作者自己写的名字。
     * @param preset 预设表里的一行。
     * @returns {{name: string, description: string|undefined}}
     */
    function displayText(preset) {
      const built = BUILT_IN[preset.id]
      const shipped =
        built !== undefined &&
        (preset.trust === 'system' || preset.name === undefined || preset.name === preset.id)
      if (shipped) return built
      return { name: preset.name ?? preset.id, description: preset.description }
    }

    /** 主题是否处于深色模式（用于给浮层选对底色）。 */
    function prefersDark() {
      if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return true
      try {
        return window.matchMedia('(prefers-color-scheme: dark)').matches
      } catch {
        return true
      }
    }

    /**
     * 浮层底色。
     * 这里刻意不读主题令牌：菜单可能被 portal 到 document.body，
     * 令牌在那个作用域上会解析成偏浅的兜底色（实测 #5F666E），
     * 与界面的深色表面完全不搭。直接用出厂浮层实测色，最确定。
     */
    function overlayColor() {
      return prefersDark() ? '#2C2E34' : '#FFFFFF'
    }

    /** 浮层描边色：与出厂浮层同一档，不依赖令牌作用域。 */
    function overlayBorder() {
      return prefersDark() ? 'rgba(255, 255, 255, .10)' : 'rgba(0, 0, 0, .08)'
    }

    /** 菜单容器：出厂浮层配色 + 贴住按钮的 fixed 定位，绝不被裁剪。 */
    function menuStyle(anchor) {
      const style = {
        position: 'fixed',
        zIndex: 2147483000,
        minWidth: 280,
        maxWidth: 360,
        maxHeight: 420,
        overflowY: 'auto',
        padding: 6,
        border: '1px solid ' + overlayBorder(),
        borderRadius: 12,
        background: overlayColor(),
        boxShadow: '0 12px 32px rgba(0, 0, 0, .32)',
      }
      if (anchor !== undefined) {
        // 贴住按钮左下角；空间不够时向上翻。
        const below = anchor.top + anchor.height + 6
        const roomBelow = window.innerHeight - below
        if (roomBelow < 260 && anchor.top > 280) {
          style.bottom = window.innerHeight - anchor.top + 6
        } else {
          style.top = below
        }
        style.left = Math.max(8, Math.min(anchor.left, window.innerWidth - 372))
      }
      return style
    }

    /** 菜单项样式。 */
    function itemStyle(active) {
      const dark = prefersDark()
      return {
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        width: '100%',
        padding: '8px 10px',
        border: 'none',
        borderRadius: 8,
        background: active ? (dark ? 'rgba(255, 255, 255, .08)' : 'rgba(0, 0, 0, .06)') : 'transparent',
        color: dark ? '#EDEDED' : '#1A1A1A',
        font: 'inherit',
        fontSize: 13,
        textAlign: 'left',
        cursor: 'pointer',
      }
    }

    /** 菜单项里的描述行：比名称更淡一档。 */
    const itemDescStyle = {
      color: prefersDark() ? 'rgba(237, 237, 237, .62)' : 'rgba(26, 26, 26, .6)',
      fontSize: 12,
      lineHeight: '16px',
      whiteSpace: 'normal',
    }

    /** 菜单项里的名称行。 */
    const itemNameStyle = {
      color: prefersDark() ? '#EDEDED' : '#1A1A1A',
      fontSize: 13,
      lineHeight: '20px',
    }

    function apply(ctx) {
      const remote = ctx.remote
      if (remote === undefined || remote.agentPresets === undefined) {
        console.error('preset-switcher: remote.agentPresets 不可用，未注册界面')
        return
      }

      /**
       * 会话标题栏里的预设切换器。
       * @param props 槽位注入的属性，含 sessionId 与 useSessions。
       */
      function PresetSwitcher(props) {
        const sessionId = props.sessionId
        const useSessions = props.useSessions

        // 本会话实际在跑的预设，来自会话投影。
        const current = useSessions((state) => {
          const value = state.byId[sessionId]?.projectionValues?.agentPreset
          return typeof value === 'string' ? value : undefined
        })

        const rootRef = React.useRef(null)
        const [presets, setPresets] = React.useState([])
        const [open, setOpen] = React.useState(false)
        const [anchor, setAnchor] = React.useState(undefined)
        const [busy, setBusy] = React.useState(false)
        const [refusal, setRefusal] = React.useState(null)
        /**
         * 同步的「正在切换」锁。
         *
         * busy 是 state，setBusy(true) 要等下一次渲染才可见；同一帧内的两次点击
         * 都会读到 busy=false 并各自发出请求。宿主虽会串行执行，但结果是「点一次切两次」，
         * 第二次还可能把预设切回去。ref 在赋值瞬间就生效，能真正挡住重入。
         */
        const busyRef = React.useRef(false)

        React.useEffect(() => {
          let alive = true
          const read = async () => {
            try {
              const result = await remote.agentPresets.list()
              if (alive) setPresets(result.ok ? (result.value.presets ?? []) : [])
            } catch {
              if (alive) setPresets([])
            }
          }
          read()
          return () => {
            alive = false
          }
        }, [])

        // 点外部关闭与 Esc 关闭。
        //
        // 用 click 而不是 mousedown：mousedown 先于 click 触发，一旦在这里
        // 判定成「外部点击」并关闭菜单，菜单项会在 click 到达之前被卸载，
        // 菜单项的 onClick 永远不会执行——表现就是「能点开但点了没反应」。
        // 改用 click 后，菜单项自己的 click 先派发（React 在根容器上监听），
        // 再轮到 document 上的这个监听器，顺序天然正确。
        React.useEffect(() => {
          if (!open) return undefined
          const onDocumentClick = (event) => {
            const inRoot = rootRef.current !== null && rootRef.current.contains(event.target)
            if (inRoot) return
            const inMenu =
              event.target instanceof Element &&
              event.target.closest('[data-preset-switcher-menu]') !== null
            if (inMenu) return
            setOpen(false)
          }
          const onKeyDown = (event) => {
            if (event.key === 'Escape') setOpen(false)
          }
          document.addEventListener('click', onDocumentClick)
          document.addEventListener('keydown', onKeyDown)
          return () => {
            document.removeEventListener('click', onDocumentClick)
            document.removeEventListener('keydown', onKeyDown)
          }
        }, [open])

        // 菜单项点击用「原生事件 + 捕获阶段」兜底。
        //
        // 菜单通过 createPortal 挂在 document.body 上，不在本组件的 DOM 子树里。
        // 依赖 React 合成事件时，事件要从 portal 容器冒泡回 React 根容器才被派发，
        // 这条路径一旦不成立，onClick 就永远不执行——表现正是「菜单能打开、点了没反应」。
        // 这里直接在 document 捕获阶段用原生监听器接管：只要点到带 data-preset-id
        // 的元素就立刻执行切换，不依赖任何 React 事件传播。
        React.useEffect(() => {
          if (!open) return undefined
          const onNativeClick = (event) => {
            const target = event.target
            if (!(target instanceof Element)) return
            const item = target.closest('[data-preset-id]')
            if (item === null) return
            const id = item.getAttribute('data-preset-id')
            if (id === null || id === '') return
            // 抢占：不让 document 冒泡阶段的「点外部关闭」先跑，避免菜单先卸载。
            event.preventDefault()
            event.stopPropagation()
            void pick(id)
          }
          document.addEventListener('click', onNativeClick, true)
          return () => document.removeEventListener('click', onNativeClick, true)
        }, [open, busy, current, sessionId])

        if (current === undefined) return null

        // 不可用的预设不提供选择，避免把「加载失败」的发现推迟到建会话时。
        const options = presets.filter((entry) => entry.broken === undefined)
        const chosen = presets.find((entry) => entry.id === current)
        // v9 标记：肉眼可见，用来确认新代码是否真的被加载。
        // busy 时显示进度，让等待期有可见反馈。
        const label = busy
          ? '切换中…'
          : (chosen === undefined ? current : displayText(chosen).name) + ' ·v11'

        const pick = async (id) => {
          setOpen(false)
          // 用 ref 做同步锁，而不是只看 busy 这个 state。
          // setBusy(true) 要等下一次渲染才生效，两次点击若发生在同一帧内，
          // 两次都会读到 busy=false 并各自发出一次请求——宿主端会串行执行，
          // 表现为「点一次却切了两次」，且第二次可能把预设切回去。
          if (busyRef.current) return
          if (id === current) return
          busyRef.current = true
          setBusy(true)
          // 宿主在会话有轮次运行时不会硬切，而是等轮次结束后再切（最长约 3 分钟）。
          // 这段等待期必须给用户可见的反馈，否则就是「点了没反应」。
          setRefusal('正在切换…若会话正在运行任务，会自动等它结束后切换')
          try {
            // 客户端超时只做「宿主彻底失联」的兜底，必须**晚于**宿主自己的兜底超时。
            // 宿主预算是：等待轮次 ≤180s + 内核动作，整次调用封顶 200s。
            // 这里取 215s，留 15s 余量让宿主先给出明确错误（失败原因比「未确认」有用得多）。
            // 若反过来（客户端先超时），界面会报失败而宿主随后真的切成功——状态就骗人了。
            const CLIENT_TIMEOUT_MS = 215000
            let timer
            const timeout = new Promise((_, reject) => {
              timer = setTimeout(() => {
                const error = new Error('宿主长时间无响应，本次切换未确认；请再试一次')
                error.code = 'agent-preset/client-timeout'
                reject(error)
              }, CLIENT_TIMEOUT_MS)
            })
            let result
            try {
              result = await Promise.race([remote.agentPresets.select(sessionId, id), timeout])
            } finally {
              clearTimeout(timer)
            }
            // 兼容两种形状：{ok:true,value} 包装，或直接返回 preset id 字符串。
            const failed = result !== null && typeof result === 'object' && result.ok === false
            if (failed) {
              const details = result.error?.details
              setRefusal(
                '切换失败：' +
                  (details !== null && typeof details === 'object' && typeof details.reason === 'string'
                    ? details.reason
                    : (result.error?.message ?? result.error?.code ?? '未知原因')) +
                  '（点击关闭）',
              )
            } else {
              setRefusal(null)
            }
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error)
            setRefusal('切换失败：' + message + '（点击关闭）')
          } finally {
            busyRef.current = false
            setBusy(false)
          }
        }

        /** 打开菜单前记录按钮位置，供 fixed 定位使用。 */
        const toggle = (event) => {
          setRefusal(null)
          const node = event.currentTarget
          const rect = node.getBoundingClientRect()
          setAnchor({ top: rect.top, bottom: rect.bottom, left: rect.left, height: rect.height })
          setOpen((value) => !value)
        }

        const trigger = h(
          'button',
          {
            type: 'button',
            ref: rootRef,
            className: CSS.seat,
            'aria-haspopup': 'menu',
            'aria-expanded': open,
            title: busy ? '正在切换，请稍候' : '切换本会话的智能体预设（模式）',
            disabled: options.length === 0,
            onClick: toggle,
          },
          IconAgentPreset === undefined
            ? h(
                'svg',
                { key: 'i', width: 14, height: 14, viewBox: '0 0 16 16', 'aria-hidden': true, style: { flex: 'none' } },
                h('circle', { cx: 8, cy: 8, r: 6.2, fill: 'none', stroke: 'currentColor', strokeWidth: 1.3 }),
                h('circle', { cx: 8, cy: 5.4, r: 1.5, fill: 'currentColor' }),
                h('path', {
                  d: 'M4.6 12.1c.5-2 1.8-3 3.4-3s2.9 1 3.4 3',
                  fill: 'none',
                  stroke: 'currentColor',
                  strokeWidth: 1.3,
                  strokeLinecap: 'round',
                }),
              )
            : h(IconAgentPreset, { key: 'i', className: CSS.seatIcon }),
          h('span', { key: 'l', className: CSS.seatLabel }, label),
          IconChevronDown === undefined
            ? h('span', { key: 'c', style: { fontSize: 9, opacity: 0.7 } }, '▾')
            : h(IconChevronDown, { key: 'c', className: CSS.chevron }),
        )

        const menuBody = h(
          'div',
          { style: menuStyle(anchor), role: 'menu', 'data-preset-switcher-menu': '' },
          options.map((entry) => {
            const active = entry.id === current
            const text = displayText(entry)
            return h(
              'button',
              {
                key: entry.id,
                type: 'button',
                role: 'menuitemradio',
                'aria-checked': active,
                disabled: busy,
                // 供 document 捕获阶段的原生监听器识别，不依赖 React 合成事件。
                'data-preset-id': entry.id,
                style: itemStyle(active),
                onClick: () => pick(entry.id),
              },
              h('span', { key: 'n', style: itemNameStyle }, text.name),
              h('span', { key: 'd', style: itemDescStyle }, text.description ?? '暂无描述。'),
            )
          }),
        )

        const menu =
          !open || options.length === 0
            ? null
            : createPortal !== undefined
              ? createPortal(menuBody, document.body)
              : menuBody

        // 提示浮层：标题栏空间窄，内联小字会被裁掉、用户看不到。
        // 「正在切换」用中性色，「失败」用告警色，避免等待期被误读成报错。
        const refusalIsError = refusal !== null && refusal.startsWith('切换失败')
        const refusalToast =
          refusal === null
            ? null
            : h(
                'div',
                {
                  role: refusalIsError ? 'alert' : 'status',
                  'data-preset-switcher-menu': '',
                  style: {
                    position: 'fixed',
                    top: 64,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    zIndex: 2147483001,
                    maxWidth: 520,
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: '1px solid ' + overlayBorder(),
                    background: refusalIsError
                      ? prefersDark()
                        ? '#3A2224'
                        : '#FFF1F0'
                      : prefersDark()
                        ? '#2C2E34'
                        : '#FFFFFF',
                    color: refusalIsError
                      ? prefersDark()
                        ? '#FFB4B4'
                        : '#A8071A'
                      : prefersDark()
                        ? '#E6E6E6'
                        : '#1F2329',
                    fontSize: 13,
                    lineHeight: '20px',
                    boxShadow: '0 8px 24px rgba(0, 0, 0, .35)',
                  },
                  onClick: () => setRefusal(null),
                },
                refusal,
              )

        return h(
          'span',
          { style: { display: 'inline-flex', alignItems: 'center', gap: 6 } },
          trigger,
          refusalToast === null ? null : (createPortal !== undefined ? createPortal(refusalToast, document.body) : refusalToast),
          menu,
        )
      }

      ctx.slots.inject('conversation.session.header.actions', () => {
        return ctx.slots.register({ name: 'conversation.session.header.actions', id: 'agent-preset', order: -10 }, PresetSwitcher)
      })
    }

    return {
      inject: ['slots', 'sessions', 'remote', 'remote.agentPresets'],
      apply,
    }
  },
})
