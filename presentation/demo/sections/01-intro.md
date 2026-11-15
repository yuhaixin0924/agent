---
layout: default
class: intro-cover
---

<div class="intro-kicker">DSH plugin / Internship assistant</div>

# DSH实习信息助手

<div class="cover-tagline">
  <div class="tagline-bubble bubble-left">让推荐有依据</div>
  <div class="tagline-bubble bubble-right">让用户能追问</div>
</div>

<div class="intro-footer">主讲人：喻海欣 周潇楠<br>日期：2026.11.27</div>

<div class="cover-speech">实习？</div>
<img class="cover-character" src="/assets/thinking-character.png" alt="思考实习问题的绿色头发卡通女孩" />

<!--
引入共约 1 分 30 秒。封面约 10 秒。
我们做的是 DSH 中的实习插件，希望把个人条件、岗位原文与分析依据连在一起。
项目名称暂用“DSH 实习插件”，后续可替换为正式名称。
-->

---
layout: default
class: agenda-page
routeAlias: agenda
---

<div class="agenda-panel">
  <h1>目录</h1>
  <Link to="intro" class="agenda-item"><span>01</span><strong>引入</strong></Link>
  <Link to="architecture" class="agenda-item"><span>02</span><strong>框架与技术介绍</strong></Link>
  <Link to="demo" class="agenda-item"><span>03</span><strong>功能的实操展示</strong></Link>
  <Link to="limitations" class="agenda-item"><span>04</span><strong>局限与改进</strong></Link>
  <Link to="closing" class="agenda-item"><span>05</span><strong>总结</strong></Link>
</div>


---
layout: default
class: chapter-page
routeAlias: intro
---

<Link to="agenda" class="chapter-number" aria-label="目录">01</Link>

# 引入

<p class="chapter-lead">找到岗位之后，才开始真正的选择</p>


---
layout: default
---

<div class="intro-kicker">01 / 引入</div>

# 找到岗位之后，才开始真正的选择

<p class="intro-lead">想找 Python / Agent 方向实习的我，打开了几个招聘页面。</p>

<div class="intro-scenario">
  <div class="intro-person">
    <div class="intro-person-label">我的条件</div>
    <strong>大三 · 广州</strong>
    <p>Python / SQL / Git<br>每周到岗 <b>2 天</b><br>可持续 6 个月</p>
    <small>虚构演示情景</small>
  </div>
  <div class="intro-questions">
    <div v-click>标题很合适，<strong>出勤要求能满足吗？</strong></div>
    <div v-click>写着 Agent 优先，<strong>实际工作会做什么？</strong></div>
    <div v-click>看见了推荐，<strong>判断的依据在哪里？</strong></div>
  </div>
</div>

<!--
想象一下，我们想找一份 Python 或 Agent 方向的实习，打开了几个招聘页面。
岗位标题看起来都相关，但点进去才发现，有的要求每周到岗五天，有的只是把 Agent 写在优先条件里，实际工作是什么还不清楚。
找到岗位之后，我们仍然要把这些信息和自己的情况逐一对照。
此页是情景描述，不是真实岗位分析结果。
-->

---
layout: default
---

<div class="intro-kicker">02 / 开发动机</div>

# 让实习分析更贴近个人，也更有依据

<p class="intro-lead">把个人条件和岗位信息，放到同一个分析流程里。</p>

<div class="intro-goals">
  <div><span>01</span><section><h2>结合个人条件</h2><p>对照城市、出勤、时长与技能，分析是否适合。</p></section></div>
  <div v-click><span>02</span><section><h2>保留原文依据</h2><p>说明岗位事实来自哪里，哪些信息仍然未知。</p></section></div>
  <div v-click><span>03</span><section><h2>支持继续追问</h2><p>不理解某个判断时，能问“为什么”，再核对证据。</p></section></div>
</div>

<!--
约 35～40 秒，两次点击。
这让我们想到：能不能把个人条件和岗位信息放到同一个分析流程里？
它既能指出哪些条件需要注意，也能保留原文依据；当我们不理解某个判断时，还能继续问“为什么”。
带着这个目标，我们开发了 DSH 中的实习插件。
交接：先由我的同伴说明宿主、模型和插件怎样配合，再回到实际操作。
这里介绍开发目标，实际实现程度由后面的实操展示支撑。
-->
