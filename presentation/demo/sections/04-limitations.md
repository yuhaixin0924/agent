---
layout: default
class: decorated-page
routeAlias: limitations
---

<div class="intro-kicker">04 / 局限与改进</div>
<img class="slide-character" src="/assets/mofuchen-orange-question.webp" alt="" />

# 岗位从哪里来？接下来怎么改？

<div class="limits-light">
  <section class="limits-card sources">
    <span>现在遇到的问题</span>
    <h2>找到、读到、确认有效</h2>
    <ul>
      <li>DSH 搜索线索，结果可能混入攻略和公告</li>
      <li>登录或动态页面可能读不到完整正文</li>
      <li>岗位会过期，工具也需要实际调用</li>
    </ul>
  </section>
  <section class="limits-card next">
    <span>接下来优先做</span>
    <h2>先把来源和验证做好</h2>
    <ul>
      <li>测试公开的学校和企业招聘页面</li>
      <li>展示来源、读取时间和待确认信息</li>
      <li>用真实岗位对照检查提取和匹配效果</li>
    </ul>
  </section>
</div>

<!--
数据来源：DSH 搜索工具提供线索，插件生成查询计划，接收限定来源的链接并尝试读取公开网页；来源包括牛客、部分学校就业网、企业招聘页等。白名单只表示允许尝试，不能说明一定读得到或已接入招聘接口。
2026-11-11 旧版小测试：人工选的五个页面读到正文并人工保存引用，另外三条指向官网的链接未读到完整正文。这只是小样本，不代表全自动效果或整体成功率。
改进：先测试一小批公开来源的岗位详情率和正文读取率，再改进时效复检与未知项提示；拿人工核对的真实岗位和不同用户条件，检查关键条件提取和推荐理由。
工具被调用才会检查，未来可以在最终报告增加步骤完成状态检查；岗位是否仍在招也需要回到招聘方页面确认。
交回同伴：目前先把有依据、可核对的流程做实，再继续完善来源和体验。
-->
