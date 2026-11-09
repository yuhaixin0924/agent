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
      react.useEffect(() => {
        if (!open) return
        const onKey = (event) => { if (event.key === "Escape") setOpen(false) }
        window.addEventListener("keydown", onKey)
        return () => window.removeEventListener("keydown", onKey)
      }, [open])
      const frame = h("iframe", {
        className: "dshib-frame",
        title: "实习候选看板",
        src: `/dsh-internship/candidates.html?v=${nonce}`
      })
      const panel = h("div", {className: "dshib-panel"},
        h("div", {className: "dshib-head"},
          h("span", {className: "dshib-title"}, "实习候选看板"),
          h("button", {className: "dshib-btn", onClick: () => setNonce((n) => n + 1)}, "刷新"),
          h("button", {className: "dshib-btn", onClick: () => window.open(`/dsh-internship/candidates.html?v=${nonce}`, "_blank", "noopener")}, "新窗口"),
          h("button", {className: "dshib-btn", onClick: () => setOpen(false)}, "关闭")
        ),
        frame
      )
      const overlay = h("div", {
        className: "dshib-overlay",
        onMouseDown: (event) => { if (event.target === event.currentTarget) setOpen(false) }
      }, panel)
      return h(react.Fragment, null,
        h("button", {
          className: "dshib-trigger",
          title: "打开实习候选看板",
          onClick: () => setOpen((v) => !v)
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
