---
layout: default
class: demo-page
routeAlias: demo
---

<div class="demo-label">03 / 同一批岗位，两份简历</div>

# 条件只差一点，推荐会有什么不同？

<div class="resume-pair">
  <section class="resume-sheet">
    <div class="resume-name">简历 A <span>出勤受限</span></div>
    <p>大三本科 · 广州<br>求职方向：Python / 后端 / Agent</p>
    <dl><dt>已掌握</dt><dd>Python · SQL · Git</dd><dt>正在学习</dt><dd>Agent 开发 · FastAPI</dd><dt>项目经历</dt><dd>Python 课程项目、基础后端练习</dd></dl>
    <div class="resume-availability">每周 <b>2 天</b><span>持续 6 个月</span></div>
  </section>
  <section class="resume-sheet">
    <div class="resume-name">简历 B <span>可全周到岗</span></div>
    <p>大三本科 · 广州<br>求职方向：Python / 后端 / Agent</p>
    <dl><dt>已掌握</dt><dd>Python · SQL · Git</dd><dt>正在学习</dt><dd>Agent 开发 · FastAPI</dd><dt>项目经历</dt><dd>Python 课程项目、基础后端练习</dd></dl>
    <div class="resume-availability">每周 <b>5 天</b><span>持续 6 个月</span></div>
  </section>
</div>

<p class="demo-caption">两份虚构演示简历，仅改变每周出勤天数。</p>

<!--
约 45 秒。这两份简历暂用已有 profiles A/B 的信息，之后可换成正式演示材料。
讲解：我们先看两个求职者，方向、技能和经历相同，只有每周可到岗天数不同。接下来给他们看同一批岗位。
实际接入：当前插件读取 dataDir 下的 profile.json，不能把此页展示说成已经实现了自动简历解析或多用户管理。
演示前用独立数据目录，把 A、B 依次放成 profile.json；各开新对话并调用 internship_profile 确认读取成功。不覆盖私人档案。
-->

---
layout: default
class: demo-page
routeAlias: demo-compare
---

<div class="demo-label">03 / 同一批岗位，两份简历</div>

# 岗位相同，分别给出推荐与依据

<div class="demo-request">
  <p>请结合当前个人档案，分析这批岗位：〈同一组岗位链接〉。</p>
  <p>逐项说明推荐建议、理由和原文依据；对照技能、城市、出勤与时长，缺失信息保留为未知。</p>
</div>

<div class="compare-lines">
  <div><span>岗位事实</span><p>原文要求与来源是否一致？</p></div>
  <div><span>推荐差异</span><p>哪些岗位的建议因出勤条件改变？</p></div>
  <div><span>判断依据</span><p>差异能否对应到简历条件与原文要求？</p></div>
</div>

<!--
约 2 分钟，主要时间用于 DSH 实操。这里不预填推荐名单或排名。
准备两三条真实岗位，至少一条原文明示出勤要求。固定同一组链接，必要时复用同一批原文快照，避免搜索变化影响对照。
先展示 A 已加载的档案并分析，再换 B、新建对话、确认档案，发送相同问题。
B 的后续话术：请对同一批岗位依据当前档案重新分析，指出哪些判断因出勤条件改变。招聘事实不变，不沿用旧结论，其他缺失条件继续保留未知。
现场并排看真实输出。A/B 出勤变化不保证一定产生不同推荐，也不意味着 B 满足其他条件。若没有差异，解释实际原因。
-->

---
layout: default
class: demo-page
routeAlias: demo-question
---

<div class="demo-label">03 / 追问、质疑与修改</div>

# 这个推荐，为什么适合我？

<div class="demo-dialogue demo-speakers">
  <div class="demo-question"><img class="questioner-avatar" src="/assets/questioner-green.png" alt="" /><span>追问依据</span><p>你为什么推荐这个岗位？请把岗位原文要求和我的对应条件放在一起，解释判断过程。</p></div>
  <div class="demo-question"><img class="questioner-avatar" src="/assets/questioner-brown.png" alt="" /><span>质疑推论</span><p>如果原文只是“熟悉 Agent 开发者优先”，能说明实际工作会做 Agent 吗？请核对职责与要求，证据不足就修改表述。</p></div>
</div>

<p class="demo-takeaway">从“给了什么结论”，继续问到“为什么得出这个结论”。</p>

<!--
约 1 分钟。先回到刚才真实生成的分析，再选一条适用的问题发送。
第一条适合分析本来就正确的情况；第二条只在岗位原文有相应表述、分析存在对应推论时使用，不诱导模型先犯错。
观察是否重新核对原文上下文，能否说明任职要求和工作职责的区别。模型可修正，也可依据证据维持原判断。
-->

---
layout: default
class: demo-page
routeAlias: demo-revise
---

<div class="demo-label">03 / 追问、质疑与修改</div>

# 把质疑说具体，再看分析怎样变化

<div class="demo-dialogue demo-speakers">
  <div class="demo-question"><img class="questioner-avatar" src="/assets/questioner-purple.png" alt="" /><span>核对未知信息</span><p>你关于远程办公的判断，依据是哪一句？请给出原文和来源；没有明确说明，就改为“未知”。</p></div>
  <div class="demo-question"><img class="questioner-avatar" src="/assets/questioner-teal-hat.png" alt="" /><span>要求修改结果</span><p>请重新核对出勤要求，把不满足我每周到岗天数的岗位单列；依据不足的建议改为“待确认”，并说明修改了什么、为什么。</p></div>
</div>

<div class="revision-focus"><span>原结论</span><i>→</i><span>原文核对</span><i>→</i><span>修改或保留，并解释</span></div>

<!--
约 1 分 30 秒。核对未知信息的提问可按实际输出改成转正、住宿等，不假设系统一定声称支持远程。
发送第二条前确认当前档案，展示重新生成的结果，对照修改前后以及实际引用。
展示的是对话内核对与修改；没有验证数据库更新时，不说偏好已保存、反馈已学习或排行榜已持久化重排。
交接：刚才看到个人条件怎样影响分析，以及用户怎样追问和要求修改。但有引用仍不意味着每个推论都可靠，下面交给同伴介绍局限与改进。
-->
