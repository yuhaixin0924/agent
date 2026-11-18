<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

// 教学动画：仅切换示意状态，不执行搜索或调用模型。
const root = ref(null)
const current = ref(-1)
const playing = ref(false)
let timer = null
let observer = null
const steps = [
  { x: 18, y: 16, number: '01', title: '发现线索', actor: '搜索 + 候选整理',
    titleDetail: '先找一些线索', body: '模型提出搜索，DSH 调用搜索工具，插件整理找到的链接。', example: '例：找到一个 Agent 实习链接', principle: '大家一起完成', meaning: '模型选择行动，DSH 调度，插件处理具体任务。' },
  { x: 202, y: 16, number: '02', title: '读取原文', actor: '网页 + 快照',
    titleDetail: '点进去读一读', body: '插件尝试读取网页，把当时读到的内容保存下来。', example: '例：查看岗位职责和时间要求', principle: '留个依据', meaning: '记录网页来源、原文和读取时间。' },
  { x: 386, y: 16, number: '03', title: '核对证据', actor: '引用 + 校验',
    titleDetail: '看看引用对不对', body: '插件逐条核对引用，有问题时指出具体位置。', example: '例：检查“每周至少到岗 4 天”', principle: '方便回看', meaning: '找到分析对应的原文。' },
  { x: 386, y: 151, number: '04', title: '结合画像', actor: '规则 + 分析',
    titleDetail: '再看看和我合不合适', body: '程序比较部分明确条件，模型结合原文解释。', example: '例：比对每周到岗天数', principle: '先看实际条件', meaning: '到岗时间和可以慢慢学的技能分开考虑。' },
  { x: 202, y: 151, number: '05', title: '判断下一步', actor: '补充 / 整理',
    titleDetail: '接下来怎么做', body: '信息不够时，模型可以继续搜索，或列出需要问的问题。', example: '例：年级要求没写，可以向招聘方问一问', principle: '留着以后确认', meaning: '最后结合原文，由用户自己决定。' },
]
const selected = computed(() => current.value < 0 ? null : steps[current.value])
function stop() {
  playing.value = false
  if (timer !== null) clearInterval(timer)
  timer = null
}
function next() { current.value = (current.value + 1) % steps.length }
function toggle() {
  if (playing.value) { stop(); return }
  if (current.value < 0) current.value = 0
  playing.value = true
  timer = setInterval(next, 2600)
}
function reset() { stop(); current.value = -1 }
function choose(index) { stop(); current.value = index }
onMounted(() => {
  // 离开页面后停止计时，回到这一页仍可继续手动讲解。
  if (typeof IntersectionObserver !== 'undefined' && root.value) {
    observer = new IntersectionObserver(entries => {
      if (!entries[0]?.isIntersecting) stop()
    })
    observer.observe(root.value)
  }
})
onUnmounted(() => { stop(); observer?.disconnect() })
</script>

<template>
  <section ref="root" class="agent-loop" aria-label="实习助手核心循环示意动画">
    <div class="loop-layout">
      <div class="loop-canvas">
        <svg viewBox="0 0 550 254" class="loop-svg" role="group" aria-label="发现线索、读取原文、核对证据、结合画像、判断下一步">
          <defs>
            <marker id="loop-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 Z" fill="#6bcabd" /></marker>
            <marker id="loop-arrow-muted" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 Z" fill="#637d8e" /></marker>
          </defs>
          <path d="M 164 50 H 198" class="connection" :class="{ lit: current === 1, moving: playing && current === 1 }" marker-end="url(#loop-arrow)" />
          <path d="M 348 50 H 382" class="connection" :class="{ lit: current === 2, moving: playing && current === 2 }" marker-end="url(#loop-arrow)" />
          <path d="M 459 84 V 147" class="connection" :class="{ lit: current === 3, moving: playing && current === 3 }" marker-end="url(#loop-arrow)" />
          <path d="M 386 185 H 352" class="connection" :class="{ lit: current === 4, moving: playing && current === 4 }" marker-end="url(#loop-arrow)" />
          <path d="M 202 185 H 92 V 88" class="connection feedback" :class="{ lit: current === 4, moving: playing && current === 4 }" marker-end="url(#loop-arrow)" />
          <text x="26" y="132" class="edge-label">可补充搜索</text>
          <path d="M 275 219 V 236 H 485" class="connection result-path" marker-end="url(#loop-arrow-muted)" />
          <text x="300" y="249" class="edge-label">整理结果 → 用户确认</text>
          <g v-for="(step, index) in steps" :key="step.number" :transform="`translate(${step.x},${step.y})`"
             class="loop-node" :class="{ active: current === index }" role="button" tabindex="0"
             :aria-label="`第 ${step.number} 步：${step.title}`" :aria-pressed="current === index" @click.stop="choose(index)" @keydown.enter.stop.prevent="choose(index)" @keydown.space.stop.prevent="choose(index)">
            <rect width="146" height="68" rx="9" />
            <text x="13" y="21" class="node-num">{{ step.number }}</text>
            <text x="13" y="41" class="node-title">{{ step.title }}</text>
            <text x="13" y="57" class="node-actor">{{ step.actor }}</text>
          </g>
        </svg>
      </div>
      <aside class="loop-aside" aria-live="polite">
        <template v-if="selected">
          <span class="aside-kicker">{{ selected.number }} / 05</span>
          <h3>{{ selected.titleDetail }}</h3>
          <p class="aside-body">{{ selected.body }}</p>
          <div class="example-box">{{ selected.example }}</div>
          <div class="principle"><span>{{ selected.principle }}</span><p>{{ selected.meaning }}</p></div>
        </template>
        <template v-else>
          <span class="aside-kicker">从需求出发</span>
          <h3>一条岗位，逐步核对</h3>
          <p class="aside-body">搜索、读取、校验、分析，然后决定下一步。</p>
          <div class="example-box">例：关注 Agent 实习的工作内容与到岗要求</div>
          <div class="principle"><span>用户做决定</span><p>插件提供依据，用户确认下一步。</p></div>
        </template>
      </aside>
    </div>
    <div class="loop-bottom">
      <div class="controls">
        <button type="button" class="primary" @click.stop="toggle">{{ playing ? '暂停' : current < 0 ? '播放' : '继续' }}</button>
        <button type="button" @click.stop="stop(); next()">下一步</button>
        <button type="button" @click.stop="reset">重置</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.agent-loop { margin-top: 5px; }
.loop-layout { display: grid; grid-template-columns: 1.58fr 1fr; gap: 15px; align-items: stretch; }
.loop-canvas { border: 1px solid #344c5e; background: #142334; border-radius: 10px; padding: 6px 3px 2px; }
.loop-svg { display: block; width: 100%; height: auto; overflow: visible; }
.connection { fill: none; stroke: #557486; stroke-width: 2; opacity: .72; }
.connection.lit { stroke: #68ddd0; stroke-width: 3; opacity: 1; }
.connection.feedback { stroke-dasharray: 5 5; }
.connection.moving { stroke-dasharray: 7 5; animation: flow 1s linear infinite; }
.connection.result-path { stroke: #6b8494; stroke-width: 1.6; }
@keyframes flow { to { stroke-dashoffset: -12; } }
.edge-label { font: 12px 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #a4b9c9; }
.loop-node { cursor: pointer; outline: none; }
.loop-node rect { fill: #1a3040; stroke: #4a6677; stroke-width: 1.4; }
.loop-node:hover rect, .loop-node:focus-visible rect, .loop-node.active rect { fill: #1a4247; stroke: #68ddd0; stroke-width: 2; }
.node-num { fill: #82ded2; font: 12px Consolas, monospace; }
.node-title { fill: #eef6f7; font: bold 17px 'PingFang SC', 'Microsoft YaHei', sans-serif; }
.node-actor { fill: #b1c6d3; font: 12px 'PingFang SC', 'Microsoft YaHei', sans-serif; }
.loop-aside { min-width: 0; padding: 17px; border: 1px solid #344c5e; border-radius: 10px; background: #172b3b; }
.aside-kicker { color: #68ddd0; font: 12px Consolas, monospace; }
.loop-aside h3 { margin: 8px 0 0; color: #eff7f7; font-size: 20px; line-height: 1.3; }
.aside-body { margin: 10px 0 0; color: #c9d8e2; font-size: 14px; line-height: 1.6; }
.example-box { margin-top: 14px; padding: 10px 11px; background: #101f2e; border-left: 2px solid #6acfc2; color: #c1d6de; font-size: 12px; line-height: 1.5; }
.principle { margin-top: 15px; padding-top: 12px; border-top: 1px solid #3c5262; }
.principle span { color: #83ddd0; font-size: 13px; font-weight: 600; }
.principle p { margin: 5px 0 0; color: #adc2cf; font-size: 12px; line-height: 1.5; }
.loop-bottom { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 12px; }
.controls { display: flex; gap: 7px; flex: none; }
.controls button { cursor: pointer; border: 1px solid #4b6b7a; border-radius: 6px; background: #1b3343; color: #d9ecea; padding: 6px 11px; font-size: 12px; }
.controls button.primary { background: #25685f; border-color: #63cbbd; color: #ecfffb; min-width: 62px; }
.controls button:hover, .controls button:focus-visible { border-color: #68ddd0; outline: none; }
.loop-bottom p { margin: 0; color: #9ab1c1; font-size: 11px; text-align: right; }
.loop-node:nth-of-type(3n + 1) rect { fill: #283b5b; stroke: #799cdb; }
.loop-node:nth-of-type(3n + 2) rect { fill: #3c3359; stroke: #aa8ad0; }
.loop-node:nth-of-type(3n) rect { fill: #1d4a49; stroke: #6dcfc1; }
.loop-node:hover rect, .loop-node:focus-visible rect, .loop-node.active rect { fill: #29655f; stroke: #8bfff0; }
.node-actor { font-size: 14px; }.controls button { font-size: 14px; padding: 8px 14px; }
@media (prefers-reduced-motion: reduce) { .connection.moving { animation: none; } }
</style>
