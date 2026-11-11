// dsh-internship browser half: a sidebar footer action that opens the
// candidates dashboard (served by the host half at /dsh-internship/candidates.html).
// Plain CommonJS-in-loader format, no build step: React is required from the
// shell's shared module table.
window.__ModuleLoader__.load({
  id: "dsh-internship",
  factory: (require) => {
    var module = {exports: {}}
    var exports = module.exports
    Object.defineProperty(exports, Symbol.toStringTag, {value: "Module"})
    const react = require("react")
    let reactDom = null
    try { reactDom = require("react-dom") } catch { reactDom = null }
    const h = react.createElement

    const CSS = `
.dshib-trigger{display:flex;align-items:center;gap:6px;width:100%;min-height:30px;padding:4px 8px;border:0;border-radius:8px;background:transparent;color:var(--dsw-alias-label-secondary);font-size:13px;line-height:20px;cursor:pointer;text-align:left}
.dshib-trigger:hover{background:var(--dsw-alias-interactive-bg-hover);color:var(--dsw-alias-label-primary)}
.dshib-dot{width:7px;height:7px;border-radius:50%;background:var(--dsw-alias-state-business-primary,#2563eb);flex:none}
.dshib-overlay{position:fixed;inset:0;z-index:1200;background:rgba(10,12,16,.42);display:flex;align-items:center;justify-content:center;padding:28px}
.dshib-panel{width:min(1180px,94vw);height:min(880px,90vh);background:var(--dsw-alias-bg-base,#fff);border:1px solid var(--dsw-alias-border-l2,#e5e7eb);border-radius:16px;box-shadow:0 24px 60px rgba(0,0,0,.28);display:flex;flex-direction:column;overflow:hidden}
.dshib-head{display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid var(--dsw-alias-border-l2,#e5e7eb)}
.dshib-title{font-size:14px;font-weight:600;color:var(--dsw-alias-label-primary,#1c1f23);flex:1}
.dshib-btn{border:1px solid var(--dsw-alias-border-l2,#e5e7eb);background:transparent;color:var(--dsw-alias-label-secondary,#6b7280);border-radius:8px;padding:4px 10px;font-size:12px;cursor:pointer}
.dshib-btn:hover{color:var(--dsw-alias-label-primary,#1c1f23)}
.dshib-frame{flex:1;width:100%;border:0;background:#fff}
`
    const TAG = "dsh-internship/dashboard.css"
    if (typeof document !== "undefined" && !document.querySelector(`style[data-plugin-css="${TAG}"]`)) {
      const style = document.createElement("style")
      style.dataset.plugin = "dsh-internship"
      style.dataset.pluginCss = TAG
      style.textContent = CSS
      document.head.appendChild(style)
    }

    function BoardAction() {
      const [open, setOpen] = react.useState(false)
      const [nonce, setNonce] = react.useState(0)
      const [tab, setTab] = react.useState('profile')
      const dirty = react.useRef(false)
      const close = () => {
        if (!dirty.current || window.confirm('档案还有尚未保存的修改，确定关闭吗？')) setOpen(false)
      }
      react.useEffect(() => {
        const onMessage = (event) => {
          if (event.origin === window.location.origin && event.data?.source === 'dsh-internship-profile') dirty.current = !!event.data.dirty
        }
        window.addEventListener('message', onMessage)
        return () => window.removeEventListener('message', onMessage)
      }, [])
      react.useEffect(() => {
        if (!open) return
        const onKey = (event) => { if (event.key === "Escape") close() }
        window.addEventListener("keydown", onKey)
        return () => window.removeEventListener("keydown", onKey)
      }, [open])
      const path = tab === 'profile' ? 'profile.html' : 'candidates.html'
      const panel = h("div", {className: "dshib-panel"},
        h("div", {className: "dshib-head"},
          h("span", {className: "dshib-title"}, "实习助手"),
          h("button", {className: "dshib-btn", 'aria-pressed': tab === 'profile', onClick: () => setTab('profile')}, "个人档案"),
          h("button", {className: "dshib-btn", 'aria-pressed': tab === 'candidates', onClick: () => setTab('candidates')}, "候选看板"),
          h("button", {className: "dshib-btn", onClick: () => { if (!dirty.current || window.confirm('刷新会放弃未保存的档案修改，继续吗？')) {dirty.current = false; setNonce((n) => n + 1)} }}, "刷新"),
          h("button", {className: "dshib-btn", onClick: () => window.open(`/dsh-internship/${path}?v=${nonce}`, "_blank", "noopener")}, "新窗口"),
          h("button", {className: "dshib-btn", onClick: close}, "关闭")
        ),
        h("iframe", {className: "dshib-frame", title: "个人实习档案", style: {display: tab === 'profile' ? 'block' : 'none'}, src: `/dsh-internship/profile.html?v=${nonce}`}),
        h("iframe", {className: "dshib-frame", title: "实习候选看板", style: {display: tab === 'candidates' ? 'block' : 'none'}, src: `/dsh-internship/candidates.html?v=${nonce}`})
      )
      const overlay = h("div", {
        className: "dshib-overlay",
        onMouseDown: (event) => { if (event.target === event.currentTarget) close() }
      }, panel)
      return h(react.Fragment, null,
        h("button", {
          className: "dshib-trigger",
          title: "打开个人档案与实习候选看板",
          onClick: () => {if (open) close(); else {dirty.current = false; setOpen(true)}}
        }, h("span", {className: "dshib-dot"}), "实习看板"),
        open ? (reactDom && reactDom.createPortal
          ? reactDom.createPortal(overlay, document.body)
          : overlay) : null
      )
    }

    const inject = ["slots"]
    function apply(ctx) {
      try {
        ctx.slots.inject("sidebar.footer.action", () => ctx.slots.register({
          name: "sidebar.footer.action",
          id: "internship-board",
          order: 40
        }, BoardAction))
      } catch (error) {
        // A UI contribution must never take the whole app down.
        console.error("[dsh-internship] sidebar panel registration failed:", error)
      }
    }
    exports.apply = apply
    exports.inject = inject
    return module.exports
  }
})
