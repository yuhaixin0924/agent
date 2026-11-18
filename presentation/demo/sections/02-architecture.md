---
layout: default
class: decorated-page
routeAlias: architecture
---

<div class="intro-kicker">02 / 框架与技术</div>
<img class="slide-character" src="/assets/mofuchen-green-question.webp" alt="" />

# 一起完成这件事的，有哪些部分？

<div class="team-light">
  <div class="person-light"><span>用户</span><strong>提出需求</strong><p>告诉助手自己的时间、方向和关注点</p></div>
  <div class="team-light-arrow">→</div>
  <div class="assistant-light">
    <b>实习助手</b>
    <div class="team-light-parts">
      <div><span>模型</span><strong>理解与判断</strong><p>理解需求、选择工具、解释结果</p></div>
      <div><span>DSH</span><strong>组织与调度</strong><p>管理对话，把请求交给工具</p></div>
      <div><span>实习插件</span><strong>处理具体任务</strong><p>整理线索、核对引用、比较条件</p></div>
    </div>
  </div>
  <div class="team-light-arrow">→</div>
  <div class="person-light result"><span>用户</span><strong>做出选择</strong><p>对照原文，确认疑问和下一步</p></div>
</div>

<!--
模型理解需求并决定调用哪些工具，DSH 组织上下文并调度，插件中的代码处理具体任务。
搜索依赖 DSH 中实际可用的搜索工具，插件的计划工具生成查询，不能独立保证搜索发生。
插件的数据目录与旧的独立 Agent 相互独立。是否调用各个工具，由运行时的模型决定。
交接：接下来沿着一条岗位线索，看看各部分怎样配合。
-->

---
layout: default
class: decorated-page
routeAlias: agent-loop
---

<div class="intro-kicker">02 / 一次可能的工作过程</div>
<img class="slide-character" src="/assets/mofuchen-green-thumbs.webp" alt="" />

# 找到一个岗位后，会发生什么？

<AgentLoop />

<!--
动画是一种示意路径，并非每次都执行全部步骤。点击播放或单点节点：发现线索、读取原文、核对证据、结合画像、判断下一步。
模型可以选择继续搜索，也可能提前结束。工具被调用后才会执行工具内部的检查；没有调用的环节不会自动完成。
网页引用通过字面校验，仍需结合上下文和招聘方页面判断语义、可信度及时效。
-->

---
layout: default
class: decorated-page
routeAlias: agent-explorer
---

<div class="intro-kicker">02 / 按需展开</div>
<img class="slide-character" src="/assets/mofuchen-green-excited.webp" alt="" />

# 点开看看，每一步怎么实现

<AgentExplorer />

<!--
点击节点查看局部流程；需要时点“查看核心代码”。
工具调用：模型提出请求，DSH 调用插件；JavaScript 的 runBridge / runPython 启动 Python 子进程，JSON 传递请求和结果。
获取岗位：DSH 搜索得到线索，插件读取公开网页并保存快照。证据校验：记录工具在已读快照中逐字查找引用，错误带条目和维度；保存一张证据卡时有错误会停止该卡的保存。
结合画像：读取本地档案，代码只对部分明确条件做初筛，模型结合原文解释。岗位要求不明时应保留未知。
交接：下面让同伴用两份档案，展示同一批岗位的分析和追问。
-->
