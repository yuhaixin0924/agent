# 独立 Agent 历史说明（归档）

> 此文档保留整理前的说明，可能引用未发布或已变化的本地文件。当前主要维护的入口是 [DSH 插件](../dsh-internship/README.md)。命令以仓库根目录为工作目录。

# 实习机会评估助手

这个项目帮助求职者收集和分析实习信息，重点核对岗位原文，并结合个人情况说明匹配理由和待确认问题。

仓库中有两个可以分别使用的部分：

- **DSH 实习插件**：在 DeepSeek Harness 中对话，使用插件管理岗位线索、证据和候选看板。新用户建议先阅读 [插件介绍与安装说明](dsh-internship/README.md)。
- **独立 Python Agent**：原有的本地实习评估程序，使用方式见下文。

两者使用独立数据；插件复用了原 Agent 的部分代码快照，但不会自动同步数据或代码。两者都不能保证招聘信息仍然有效，投递前请核对原文。

> 下文也记录了本地开发中的图形界面与对话功能；如果从 GitHub 下载后缺少 `app.py`、`requirements-ui.txt` 或相应模块，这些部分尚未随当前仓库版本发布，暂时无法按文中的命令运行。

## 独立 Python Agent

当前项目根目录就是本 README 所在的 agent 目录；源码已统一到 internship_agent/，不再需要 dist 副本或 radar_agent 包。
原有 .env 和 internship_data/ 保留在项目根目录，原来的运行命令继续可用。

根据岗位原文与个人档案，分析时间、出勤、远程、学习机会、技术差距和待遇。
招聘方陈述、模型分析、未知信息分别展示；技术暂不匹配不会在模型分析前自动淘汰岗位。

Python 3.10+，只用标准库。仓库不含示例数据、真实用户资料、密钥或数据库。

## 启动

### 本地图形界面

首次安装：`uv venv .venv-ui`，然后 `uv pip install --python .venv-ui/bin/python -r requirements-ui.txt`。
没有 uv 时可用 `python3 -m venv .venv-ui` 和 `.venv-ui/bin/python -m pip install -r requirements-ui.txt`。

```bash
.venv-ui/bin/python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

打开终端显示的本地链接。界面支持对话、档案更新前后对照、确认/舍弃更新、修改查询目标、查看进度、报告与执行错误。
只有点击发送或搜索才调用模型；普通页面重绘不自动搜索。密钥保存在原有 .env 中，不在界面展示。
单用户本地运行，沿用原有个人档案和数据库；暂不支持多用户隔离、后台任务或中断续跑。运行查询期间请保持页面连接，避免刷新或重复点击。
UI 测试：`.venv-ui/bin/python -m unittest discover -s tests -v`。

在本仓库根目录运行：

```bash
python3 -m internship_agent init
```

程序在本地生成 internship_data/profile.json、sources.json、mail.env；已有文件不会覆盖。
填写真实个人档案；priorities 是关注维度，hard_constraints 明确哪些条件不可妥协。
days_per_week 和 months 分别为可到岗天数和可持续月数，未知保留 null。

sources.json 是来源配置数组，支持三类来源：

- greenhouse：提供 type、name、board（目标公司公开招聘看板的 token）。
- rss：提供 type、name、url（HTTPS 订阅地址）。
- json：提供 type、name、path（本地真实岗位 JSON 文件的绝对路径）。

WorldQuant 的公开看板 token 为 worldquant，可用于验证真实采集；不保证岗位持续开放或适合低年级学生。
其配置可填写为 `[{"type":"greenhouse","name":"WorldQuant","board":"worldquant"}]`。
尚未实现 BOSS、实习僧或学校网站专用采集器。

```bash
python3 -m internship_agent sync
python3 -m internship_agent report
```

不加 --ai 时输出简单规则基线，不调用模型。

## 模型分析

现在可以直接对话：`python3 -m internship_agent chat`。
每轮使用已配置模型并消耗额度。直接描述需求，模型会追问关键条件、提醒取舍，并展示拟更新档案和搜索任务。
输入 `/save` 才保存展示的档案变更；`/search` 才开始按展示的任务调用搜索流程。
`/profile` 查看档案，`/new` 清空最近对话并开始新话题，`/quit` 退出。
确认后的档案跨会话保留，最近六轮对话保存于被忽略的 `internship_data/chat-history.json`；更早的对话不保留。
当前尚无完整历史检索、语义压缩或自动合并搜索报告。讨论总结与待办见 [DESIGN.md](../DESIGN.md)。

在仓库根目录本地创建 .env，填写 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL，或设置同名环境变量。
采用支持工具调用的 Chat Completions 兼容接口；基础地址后自动追加 /chat/completions。
提供商的模型ID请使用你账户实际可用的型号。不要在源码、截图或公开讨论中写入密钥。

```bash
# 将“岗位ID”替换为 report 显示的真实ID
python3 -m internship_agent report --ai --job-id 岗位ID
```

模型会收到用户档案及岗位原文，会产生提供商的API费用。
可以用 --profile 指定另一份位于 internship_data/ 内的本地档案。
结果写入 internship_data/latest-report.txt 和 latest-assessment.json，重跑会覆盖最近文件。

流程：采集与去重 → 本地岗位原文＋用户档案 → 固定批次分析 → 校验格式和引用 → 机会证据卡。
每批5条、最多6批，校验失败最多修正一次；超过30条须选择岗位或缩小输入池，不会静默漏评。
引用存在不代表推论正确，也不能证明招聘方的承诺属实。工作强度、培养质量和资格例外需本人核实。
不查询实时股价、不预测上市、不自动更新用户技能。

## 自主发现机会与补证

可靠性修复：引用不匹配会一次列出所有不匹配条目的序号、维度、页面和相近原文；提示不自动替换原引用，也不绕过校验。
连续三次工具失败后停止本轮，并保留已读页面与诊断。失败网页会附上其他已发现、尚未读取的候选链接，供模型重新选择。
画像未声明 hard_constraints 的条件默认是待确认偏好，不能按硬限制排除岗位。
`python3 -m internship_agent status` 查看数据库岗位数量和每个来源最近一次 sync 的时间、耗时、结果与错误。
空结果明确标警告；来源成功不代表覆盖完整或仍在招，目前不按缺失记录自动下架。旧来源在再次 sync 后才出现健康记录。
现有 daily 已按收件人和岗位版本记录发送去重；schedule-template 已能生成 macOS 定时配置，但需另行启用。

新增 `discover` 命令：给出目标后，模型自行选择搜索、换关键词、阅读岗位、沿页面链接补证、保存机会或停止。
原来的 `report --ai` 继续用于固定岗位池的完整评估；`discover` 的目标是有限预算内找到值得进一步考虑的机会，不承诺穷尽全网。

```bash
python3 -m internship_agent discover "寻找适合大二学生的寒假 Agent 或后端实习，重视出勤时间和真实开发任务；技能差距可以准备" --max-steps 16
```

直接运行时会读取本地 profile.json，调用已配置的模型；没有搜索密钥时可先查看本地岗位，再访问原网址和页面链接。
也可以用 `--seed-url` 指定真实招聘详情页或招聘列表页，多次使用可提供多个入口。
没有本地岗位、入口链接或搜索配置时，模型应报告缺少入口，不能编造网址。

需要全网搜索时，在**已有的根目录 .env 中追加一行** `TAVILY_API_KEY=你的搜索密钥`，保留原有模型配置。
搜索接入 [Tavily 官方 Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)，只取线索，不使用其生成式答案作为证据。
模型接口和搜索接口独立计费，以各自账户为准。搜索词会发送给 Tavily，画像和阅读结果会发送给模型提供商；密钥不会进入对话。
无需安装新 Python 库。请勿覆盖整个 .env 或把密钥写进命令行、源码。

循环：**目标与画像 → 模型选择一个工具 → 代码执行 → 观察结果和剩余预算 → 模型决定下一步**。

| 工具 | 作用 |
| --- | --- |
| list_saved_jobs / read_saved_job | 查看已有岗位及历史原文，历史采集时间保持不变 |
| search_web | 查询新岗位或需要补充的背景证据，支持更换关键词 |
| read_page | 阅读已发现的 HTTPS 页面、正文翻页，并返回可继续访问的链接 |
| record_opportunity | 保存具体岗位、逐条原文引用、来源、个人分析与未知项 |
| finish | 有结果、证据不足或需要补充信息时结束 |

默认最多16次模型请求、4次搜索、8个新网页读取尝试、10个机会；失败搜索/读取也占用预算，重复成功查询和翻阅已读正文使用缓存。
每次模型输出最多3500 tokens，累计对话超过140000字符时停止；这不是人民币费用上限。
`--max-steps` 可设1至40；`--max-seconds` 默认300、范围10至900。时间在请求之间检查，正在执行的网络请求可能使实际时间超出预算。
模型可提前结束；次数、上下文或时间用完则明确显示结果不完整，保留已找到的机会，不额外付费调用模型整理。

运行中显示工具及行动目的；`internship_data/latest-discovery.txt` 是本轮结果，`latest-discovery.json` 包含工具参数、观察、来源快照、用量和停止状态。
最近文件会覆盖，SQLite events 保留每轮的动作记录及 run_id；当前不支持中断后精确续跑。
保存的岗位进入原来的岗位库，可以继续 `report --ai --job-id 岗位ID`，或由本人创建投递草稿。
补充的企业背景单独保存在发现报告里，不塞入岗位原文；现有 report 命令只评估岗位原文本身。

证据必须逐字出现在模型已经阅读的正文片段中，不能拿搜索摘要、未读取的页面或其他岗位信息当依据。
检查能防止不存在的引用，但不能证明一句原文足以支持模型概括，也不能自动判断企业宣传是否真实、页面是否属于同一岗位。
未覆盖的维度由程序标为未取得证据。公司整体福利不能直接当实习生待遇，岗位仍在招也需核实。

网页阅读遵守 robots.txt；规则无法确认、登录、验证码、纯 JavaScript 页面或 PDF 会返回失败，由模型选择换来源。
仅访问公开 HTTPS 地址，每次 DNS 解析和重定向都检查目标，连接固定到已验证的公网 IP；工具没有读任意文件、运行命令、发送邮件或投递权限。
若本机代理使用 198.18.0.0/15 虚拟 DNS，则用 [Cloudflare DNS over HTTPS](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-json/) 查询实际地址后重新验证；不会放行虚拟或内网 IP。
公共 DNS 不可达时会给出失败原因，可关闭代理 Fake-IP 模式后重试。

## 可选邮件功能

在本地 internship_data/mail.env 填写 SMTP_HOST、SMTP_PORT、SMTP_SECURITY、SMTP_USER、SMTP_PASSWORD、SMTP_FROM、DAILY_TO。
SMTP_SECURITY 支持 ssl/starttls，DAILY_TO 填本人邮箱；模型不读取邮箱密码。

```bash
python3 -m internship_agent daily
# 下列命令才实际发送给本人
python3 -m internship_agent daily --send
```

向招聘方投递由本人核实邮箱并逐封确认：

```bash
python3 -m internship_agent draft 岗位ID --to 招聘邮箱 --resume /绝对路径/简历.pdf
python3 -m internship_agent review 邮件ID
python3 -m internship_agent send 邮件ID
```

创建草稿时保存附件快照，review 导出实际邮件和PDF。send 要求在交互终端输入与当前版本绑定的确认文字。
修改草稿：编辑导出的 draft.json，再运行 `edit 邮件ID --file 本地JSON路径`；替换附件加 --resume。
SMTP失败不盲目重试：outbox 查看 sending/uncertain 后，本人检查邮箱，再用 `reconcile 邮件ID --outcome sent` 或 not-sent 登记。
SMTP已接受不保证实际送达。程序不自动提交招聘网站表单。
schedule-template 只生成 macOS 调度文件，不自动安装；运行 --help 查看各命令。

## 测试和代码

```bash
python3 -m unittest discover -s tests -v
```

测试使用代码内的虚构夹具和模型/邮件替身，不联网、不发送、不用密钥。
core.py 负责采集与存储；research.py 负责机会分析；mail.py 负责人工审核邮件；__main__.py 串联命令。
discovery.py 负责自主动作循环和补证记录，web.py 负责公开网页阅读与搜索接口。
http.py 和 llm.py 是合并后的网络与模型适配，均位于 internship_agent/ 内。
evaluate 保留旧规则排序基线，AI排名比较已停用；新的事实准确性评测仍需人工标注。
新增测试覆盖无结果后改查、跨页补证、引用修正、缓存与预算、内网地址/重定向拦截、robots 拒绝和禁止越权工具；这些是模拟模型测试，不代表真实招聘覆盖率或模型判断准确率。

## Git 范围

.gitignore 默认忽略所有文件，仅允许明确列出的源码、此文档和测试。
init 生成的档案、邮箱配置、.env、简历、数据库、报告、调度文件、缓存都不应进入版本控制。
新增必要源码时显式更新允许清单。不要用 git add -f 绕过规则。
忽略规则不检查已允许源码中的内容，也不移除曾提交的秘密；提交前仍应检查差异。
本项目不提供真实账户配置或用户资料。
