---
theme: default
title: 实习助手 · Slidev 协作样稿
info: 用四页样稿验证内容编辑、浏览器预览与逐步展示。
colorSchema: dark
transition: fade
fonts:
  sans: 'Microsoft YaHei, PingFang SC, sans-serif'
  mono: 'Consolas, monospace'
  provider: none
drawings:
  persist: false
layout: cover
---

<div class="eyebrow">DSH 实习插件 / 协作样稿</div>

# 推荐，先有依据

从岗位原文出发，解释哪些机会值得进一步了解。

<div class="cover-note">4 页试稿 · 内容与设计均可继续修改</div>

<!--
开场约 20 秒。这是验证 Slidev 协作方式的样稿，不是完整的 15 分钟汇报。
先试切页，再试逐步展示，最后打开看板和仓库。
-->

---
layout: default
---

<div class="eyebrow">01 / 分工</div>

# 对话交给 DSH，证据交给插件

<div class="roles">
<div><span class="role-id">01</span><strong>DSH ＋ 大模型</strong><p>理解需求，选择工具，解释结果。</p></div>
<div v-click><span class="role-id">02</span><strong>我们开发的实习插件</strong><p>接收调用，安排网页读取、岗位记录与看板。</p></div>
<div v-click><span class="role-id">03</span><strong>插件的 Python 后端</strong><p>保存快照，校验引用，将结果写入 SQLite。</p></div>
</div>

<p v-click class="takeaway">独立 CLI 是另一条已有入口，当前与插件的数据不自动同步。</p>

<!--
点击三次，依次展示插件、Python 与独立 CLI 边界。
此页可以根据反馈改为结构图；先验证文字层级和逐步出现效果。
-->

---
layout: default
---

<div class="eyebrow">02 / 核心机制</div>

# 引用存在，仍需核对推论

<p class="intro">下面只展示“连续原文检查”的简化逻辑。</p>

```python {all|2-3|5-6}
def validate_quote(quote, source_text):
    if len(quote.strip()) < 4 or quote not in source_text:
        raise ValueError("引用必须来自连续原文")

    # 校验文字来源；语义与适用对象仍需核对
    return True
```

<div v-click class="example">
<span>原文：熟悉 Agent 开发者优先。</span>
<strong>尚不能据此认定：入职后一定参与 Agent 开发。</strong>
</div>

<!--
逐次点击突出校验行及校验边界，再显示反例。
这是依据真实实现提炼的教学代码，不是源码原样复制；完整代码见下一页仓库链接。
-->

---
layout: default
---

<div class="eyebrow">03 / 试一次协作</div>

# 从讲解页，进入实际界面

<div class="links">
<a href="/candidates.html" target="_blank" rel="noopener">打开候选看板预览 <span>本地空报告，用于查看布局</span></a>
<a href="https://github.com/yuhaixin0924/agent" target="_blank" rel="noopener">打开项目仓库 <span>查看源码与安装说明，需要网络</span></a>
</div>

<p class="takeaway">下一步：你指出一页要改什么，我修改源文件，你在浏览器查看更新。</p>

<p class="small-note">DSH 实操请切换到已运行的应用；此页尚未连接 DSH 服务。</p>

<!--
可以提出具体修改，例如：封面更简洁、第二页换图、第三页减少解释。
在 VS Code 修改 slides.md 后保存，浏览器会更新；只有保存到磁盘的改动才会进入预览。
-->
