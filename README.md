# 实习机会评估助手

当前项目根目录就是本 README 所在的 agent 目录；源码已统一到 internship_agent/，不再需要 dist 副本或 radar_agent 包。
原有 .env 和 internship_data/ 保留在项目根目录，原来的运行命令继续可用。

根据岗位原文与个人档案，分析时间、出勤、远程、学习机会、技术差距和待遇。
招聘方陈述、模型分析、未知信息分别展示；技术暂不匹配不会在模型分析前自动淘汰岗位。

Python 3.10+，只用标准库。仓库不含示例数据、真实用户资料、密钥或数据库。

## 启动

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
http.py 和 llm.py 是合并后的网络与模型适配，均位于 internship_agent/ 内。
evaluate 保留旧规则排序基线，AI排名比较已停用；新的事实准确性评测仍需人工标注。

## Git 范围

.gitignore 默认忽略所有文件，仅允许明确列出的源码、此文档和测试。
init 生成的档案、邮箱配置、.env、简历、数据库、报告、调度文件、缓存都不应进入版本控制。
新增必要源码时显式更新允许清单。不要用 git add -f 绕过规则。
忽略规则不检查已允许源码中的内容，也不移除曾提交的秘密；提交前仍应检查差异。
本项目不提供真实账户配置或用户资料。
