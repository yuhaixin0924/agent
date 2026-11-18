<script setup>
import { computed, ref } from 'vue'
import CodeSnippet from './CodeSnippet.vue'

// 讲解示意：不请求模型、不执行工具、不读取真实岗位。
const active = ref(null)
const showCode = ref(false)
const stages = [
  {
    id: 'call', number: '01', name: '工具调用', actor: 'DSH → 插件',
    title: '工具请求怎样交给 Python？',
    blocks: [['模型', '选择工具和参数'], ['DSH', '调度工具'], ['插件', '运行 Python']],
    detail: '模型提出请求，DSH 调用插件；runPython 启动子进程并传递 JSON。',
    outcome: 'Python 返回工具结果，DSH 继续处理。',
    file: 'src/index.js · 不同函数中的代码节选',
    code: `execute: (args, exec) =>\n  runBridge(tool, args, config, exec.signal)\n\n// runBridge 内：\nreturn runPython({tool, args}, config, signal)\n\n// runPython 内：\nchild.stdin.end(JSON.stringify(request))`,
    explanation: [['execute', 'DSH 调用的入口'], ['runPython', '启动 Python 子进程'], ['stdin / stdout', '传递请求和结果']],
    href: 'https://github.com/yuhaixin0924/agent/blob/main/dsh-internship/src/index.js',
  },
  {
    id: 'read', number: '02', name: '获取岗位', actor: '搜索与快照',
    title: '从岗位链接到网页快照',
    blocks: [['DSH 搜索', '获取链接'], ['Python', '读取公开网页'], ['SQLite', '保存原文快照']],
    detail: '插件先整理候选；读取成功后保存快照，供后续引用。',
    outcome: '获取岗位正文，同时保留来源和读取时间。',
    file: 'python/bridge.py · execute 节选',
    code: `if tool=='internship_read_page':\n    return self.snapshot(\n        WebTools().read(args['url'])\n    )`,
    explanation: [['read', '读取公开网页'], ['snapshot', '保存已读取内容'], ['page_id', '供后续引用快照']],
    href: 'https://github.com/yuhaixin0924/agent/blob/main/dsh-internship/python/bridge.py',
  },
  {
    id: 'evidence', number: '03', name: '核对证据', actor: '原文与引用',
    title: '逐字检查引用来源',
    blocks: [['网页快照', '已读原文'], ['Python', '逐条校验'], ['证据卡', '保存或报错']],
    detail: '检查引用长度，再对照已读片段；发现问题时指出条目和维度。',
    outcome: '通过检查后保存，解释仍需结合原文判断。',
    file: 'python/agent_snapshot/discovery.py · record 节选',
    code: `if len(quote.strip()) < 4 or not any(\n    quote in part for part in self.seen_text[ep]\n):\n    # 省略相近原文查找及部分字段\n    errors.append({"index": index,\n                   "dimension": dimension})\nif errors:\n    raise EvidenceError(errors)`,
    explanation: [['quote', '待检查的引用'], ['seen_text', '已经读过的正文'], ['errors', '逐条记录错误位置']],
    href: 'https://github.com/yuhaixin0924/agent/blob/main/dsh-internship/python/agent_snapshot/discovery.py',
  },
  {
    id: 'match', number: '04', name: '结合画像', actor: '规则与分析',
    title: '结合个人情况整理结果',
    blocks: [['岗位证据', '时间、地点等'], ['用户画像', '可到岗条件'], ['分析结果', '匹配点与待确认']],
    detail: '插件做有限的规则初筛；模型结合原文和档案解释结果。',
    outcome: '未知条件留给用户与招聘方确认。',
    file: 'python/bridge.py · get 节选',
    code: `p=profile(self.root)\njob=dict(job)\n# 省略地点线索检查\nm=match(job,p)`,
    explanation: [['profile', '读取用户档案'], ['job', '读取已保存岗位'], ['match', '运行规则初筛']],
    href: 'https://github.com/yuhaixin0924/agent/blob/main/dsh-internship/python/bridge.py',
  },
]
const selected = computed(() => stages.find(stage => stage.id === active.value))
function selectStage(id) {
  active.value = active.value === id ? null : id
  showCode.value = false
}
</script>

<template>
  <section class="explorer" aria-label="实习助手流程图">
    <div class="explorer-stages">
      <template v-for="(stage, index) in stages" :key="stage.id">
        <button type="button" class="stage" :class="{ selected: active === stage.id }"
          :aria-pressed="active === stage.id" @click.stop="selectStage(stage.id)">
          <span class="stage-number">{{ stage.number }}</span>
          <strong>{{ stage.name }}</strong>
          <span class="stage-actor">{{ stage.actor }}</span>
          <span class="stage-hint">{{ active === stage.id ? '收起 ↑' : '展开 ↓' }}</span>
        </button>
        <span v-if="index < stages.length - 1" class="stage-arrow" aria-hidden="true">→</span>
      </template>
    </div>

    <div class="detail-panel" aria-live="polite">
      <template v-if="!selected">
        <div class="overview-visual">
          <div class="overview-card"><span>求职需求</span><strong>时间 · 城市 · 方向</strong></div>
          <div class="overview-route"><i></i><span>搜索 → 阅读 → 核对</span><i></i></div>
          <div class="overview-card result"><span>岗位分析</span><strong>原文 · 匹配 · 待确认</strong></div>
        </div>
        <p class="overview-caption">一条需求，经过工具处理，变成可核对的岗位分析。</p>
      </template>
      <template v-else>
        <div class="detail-header">
          <div><span class="detail-label">{{ selected.number }} / {{ selected.actor }}</span><h3>{{ selected.title }}</h3></div>
          <div class="detail-actions">
            <button type="button" class="code-toggle" :aria-expanded="showCode" @click.stop="showCode = !showCode">{{ showCode ? '查看流程' : '查看核心代码' }}</button>
            <button type="button" class="close-detail" aria-label="收起细节" @click.stop="selectStage(selected.id)">×</button>
          </div>
        </div>
        <template v-if="!showCode">
          <div class="mini-flow">
            <template v-for="(block, index) in selected.blocks" :key="block[0]">
              <div class="mini-block"><b>{{ block[0] }}</b><span>{{ block[1] }}</span></div>
              <span v-if="index < selected.blocks.length - 1" class="mini-arrow">→</span>
            </template>
          </div>
          <p class="detail-text">{{ selected.detail }}</p>
          <p class="detail-result">{{ selected.outcome }}</p>
        </template>
        <template v-else>
          <div class="source-body">
            <div><CodeSnippet :code="selected.code" :language="selected.id === 'call' ? 'javascript' : 'python'" /><a class="source-link" :href="selected.href" target="_blank" rel="noopener noreferrer" @click.stop>{{ selected.file }} ↗</a></div>
            <div class="source-guide"><div v-for="item in selected.explanation" :key="item[0]"><b>{{ item[0] }}</b><span>{{ item[1] }}</span></div></div>
          </div>
        </template>
      </template>
    </div>
  </section>
</template>

<style scoped>
.explorer { margin-top: 15px; }
.explorer-stages { display: grid; grid-template-columns: 1fr 20px 1fr 20px 1fr 20px 1fr; gap: 5px; align-items: center; }
.stage { width: 100%; height: 98px; text-align: left; padding: 10px 12px; border: 1px solid #405266; border-radius: 8px; background: #162638; color: #edf2f7; cursor: pointer; }
.stage:hover, .stage:focus-visible, .stage.selected { border-color: #68ddd0; background: #183642; outline: none; }
.stage span, .stage strong { display: block; }
.stage-number { color: #68ddd0; font: 12px Consolas, monospace; }
.stage strong { font-size: 18px; margin-top: 2px; }
.stage-actor { color: #bdcad9; font-size: 12px; margin-top: 1px; }
.stage-hint { color: #77dccc; font-size: 11px; margin-top: 3px; }
.stage-arrow { text-align: center; font-size: 18px; color: #68ddd0; }
.detail-panel { height: 238px; margin-top: 13px; padding: 13px 16px; border: 1px solid #354b5d; border-radius: 9px; background: #142334; }
.overview-visual { display: grid; grid-template-columns: 1fr 1.35fr 1fr; gap: 12px; align-items: center; padding: 40px 22px 0; }
.overview-card { padding: 17px 13px; border: 1px solid #4b6879; border-radius: 8px; background: #1a3041; text-align: center; }
.overview-card.result { border-color: #4d9992; background: #173b40; }
.overview-card span, .overview-card strong { display: block; }
.overview-card span { color: #81d8cf; font-size: 12px; }
.overview-card strong { margin-top: 5px; color: #e4eff3; font-size: 15px; }
.overview-route { display: flex; align-items: center; gap: 8px; color: #afc2d2; font-size: 12px; white-space: nowrap; }
.overview-route i { height: 1px; flex: 1; background: #68ddd0; }
.overview-caption { margin: 16px 0 0; color: #9db2c3; text-align: center; font-size: 12px; }
.detail-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.detail-label { font-size: 11px; color: #68ddd0; }
.detail-header h3 { margin: 3px 0 0; font-size: 19px; line-height: 1.25; }
.detail-actions { display: flex; align-items: center; gap: 8px; }
.code-toggle, .close-detail { border: 1px solid #537184; background: #203748; color: #dcf4ee; border-radius: 6px; cursor: pointer; }
.code-toggle { padding: 6px 10px; font-size: 12px; white-space: nowrap; }
.close-detail { width: 30px; height: 30px; font-size: 18px; line-height: 1; }
.code-toggle:hover, .close-detail:hover { border-color: #68ddd0; }
.mini-flow { display: grid; grid-template-columns: 1fr 24px 1fr 24px 1fr; gap: 5px; align-items: center; margin-top: 12px; }
.mini-block { padding: 11px 12px; border-radius: 7px; background: #1d3446; border: 1px solid #3d596a; }
.mini-block b, .mini-block span { display: block; }
.mini-block b { color: #8fe1d6; font-size: 14px; }
.mini-block span { color: #c8d8e2; font-size: 12px; margin-top: 3px; }
.mini-arrow { color: #68ddd0; text-align: center; }
.detail-text { color: #d0dce7; font-size: 13px; margin: 12px 0 0; }
.detail-result { color: #9eb5c5; font-size: 12px; margin: 5px 0 0; }
.source-body { display: grid; grid-template-columns: 1.45fr 1fr; gap: 16px; margin-top: 10px; }
.source-body pre { margin: 0; min-height: 123px; max-height: 135px; padding: 9px 11px; overflow: auto; border-radius: 5px; background: #0b1723; color: #d5eee6; font: 11px/1.45 Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
.source-link { display: block; color: #82c6c0; font-size: 10px; margin-top: 4px; }
.source-guide > div { padding: 5px 0; border-bottom: 1px solid #354b5d; }
.source-guide b, .source-guide span { display: block; }
.source-guide b { color: #86dcd1; font-size: 12px; }
.source-guide span { color: #bccdd8; font-size: 12px; margin-top: 2px; }
.stage:nth-of-type(4n + 1) { background: #293d5d; border-color: #7a9bd8; }
.stage:nth-of-type(4n + 2) { background: #3a3155; border-color: #a88ace; }
.stage:nth-of-type(4n + 3) { background: #1d4847; border-color: #69c7b8; }
.stage:nth-of-type(4n) { background: #4a382f; border-color: #c9956b; }
.stage:hover, .stage:focus-visible, .stage.selected { border-color: #9ff8e7; outline: 2px solid #7ddfce; }
.stage-number, .stage-actor, .stage-hint { font-size: 13px; }
.overview-card span, .overview-route, .overview-caption { font-size: 14px; }
.detail-label, .detail-result, .source-guide b, .source-guide span { font-size: 13px; }
.mini-block span, .detail-text { font-size: 14px; }
.code-toggle, .source-link { font-size: 13px; }
</style>
