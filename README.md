# 个人信息雷达 Agent

一个便于逐步阅读、修改的轻量 Agent。仅使用 Python 3.10+ 标准库，无需安装依赖。
现阶段接入 Hacker News 帖子与评论，侧重 Agent 学习资料和开发者需求研究。
尚未接入中国高校实习/竞赛网站，也不支持全网搜索或读取外部文章正文。
已有的 `lesson1.py`、`lesson2.py`、`crawler.py` 和 `hn_items.json` 保留原样。

## 先跑起来

在项目目录执行：

```bash
python3 -m radar_agent demo
```

此模式完全离线，使用标为 Demo 的固定样例和脚本化模型替身。
它验证“模型提出工具调用 → Python 执行 → 返回工具结果 → 再调用 → 回答”的循环，
不代表真实模型具有相应判断能力，示例 ID 也不是实际证据。

独立运行真实采集工具（无需模型 Key）：

```bash
python3 -m radar_agent crawl --limit 5
python3 -m radar_agent crawl --feed ask --limit 10
```

每次运行建立新目录，默认位于项目 `runs/`，不会覆盖之前的结果。
采集过程中如有部分请求失败，会保存已取得的帖子和错误，并以 partial 状态退出。

## 接入真实模型

```bash
cp .env.example .env
```

打开 `.env`，填写以下三个值（也可使用同名环境变量，环境变量优先）：

```dotenv
LLM_API_KEY=你的密钥
LLM_BASE_URL=提供商文档中的基础地址
LLM_MODEL=支持工具调用的模型ID
```

例如基础地址的形状是 `https://api.openai.com/v1`，程序在末尾追加 `/chat/completions`。
如果提供商的路径不是 `/v1`，按其官方文档填写，不要自动加 `/v1`。
密钥只用于请求头，不进入模型上下文或运行日志。
这个适配器要求接口支持 `tools`、`tool_choice=required/auto` 和工具结果消息；
“OpenAI-compatible”并不保证所有提供商、所有模型都支持这些字段。
不会读取 Codex/ChatGPT 登录凭据，也不会自动从其他配置目录寻找密钥。

使用 DeepSeek 官方 API 时，目前可填写：

```dotenv
LLM_API_KEY=你的DeepSeek密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
```

程序自动为 `api.deepseek.com` 设置 `thinking.type=disabled`，因为官方思考模式
不支持首轮使用的 `tool_choice=required`。本版不启用 DeepSeek 思考模式。
该设置只对官方域名生效；第三方中转需按其文档核实参数。
参考：[官方接入说明](https://api-docs.deepseek.com/)、
[工具选择参数](https://api-docs.deepseek.com/api/create-chat-completion/)。

```bash
python3 -m radar_agent run "找出适合计算机大二学生学习的 Agent 项目，以及值得验证的开发者需求。每条附来源。"
```

运行会按提供商规则产生 API 费用。默认最多 6 次模型请求、12 次工具执行，
每个工具又有帖子/评论数量上限；这不是金额上限。模型 POST 失败不自动重试。
可用 `--max-steps 3` 限制模型轮数（可能导致采集完成但还没生成报告）。
本机兼容服务可使用 localhost HTTP 地址及其要求的占位 Key。

## 哪里体现 Agent 机制

`agent.py` 中的 `Agent.run()` 保存对话，循环调用模型。
模型自己选择获取哪个列表、查看哪条帖子、是否阅读评论、何时回答。
模型得到的工具调用是 JSON 数据，Python 校验后调用白名单中的函数。
工具输出再次作为 `role=tool` 消息交回模型；不是采集一次再固定分类。
返回纯文本时结束；用完预算却没有回答时标为 `budget_exhausted`，不伪装成功。
最初要求模型取证；若接口忽略要求、直接回答，标为 `no_evidence`。

工具：

| 工具 | 作用 |
| --- | --- |
| `get_posts(feed, limit, offset)` | 获取 new/top/ask/show/job 列表的一批候选，每批最多 20 条 |
| `get_post(post_id)` | 查看已知帖子详情和 HN 站内文本 |
| `get_comments(post_id, limit)` | 最多 15 条评论样本，最多检查 30 个评论节点 |

同一次运行缓存已读条目及列表快照，减少重复请求。评论按广度优先采样，不代表完整讨论。
HTML 文本转为纯文本，每条正文限制 3000 字符。结果会声明外链正文尚未读取。
工具只访问固定 HN API，不能执行 shell、任意代码、任意 URL 或任意路径写入。
帖子和评论是待分析的数据，system prompt 明确要求忽略其中的指令。
这不是完整的提示注入防护，也没有自动核验模型引用；有来源仍需人工检查结论。

## 看哪些文件

建议顺序：

1. `radar_agent/tools.py`：普通采集函数、参数说明、校验和工具注册。
2. `radar_agent/agent.py`：核心的模型—工具循环以及停止条件。
3. `radar_agent/llm.py`：对接模型接口。
4. `radar_agent/__main__.py`：命令行和结果保存。
5. `radar_agent/http.py`：网络请求、超时和错误处理。

`runs/<本次运行>/` 包含：

- `report.md`：最终回答或错误说明。
- `result.json`：状态、轮数和调用数。
- `events.jsonl`：一行一个事件，包含调用参数、工具结果和模型 usage（如果服务提供）。
- `messages.json`：Agent 的完整模型对话；crawl 模式没有此文件。
- `posts.json`：仅 crawl 模式，包含采集结果和单条错误。

`completed` 代表正常交付回答，不代表内容一定正确。没有适合的机会是允许的结果。
日志保存采集文本和任务内容，分享之前应自行检查是否包含不想公开的信息。

## 测试与排查

```bash
python3 -m unittest discover -s tests -v
python3 -m radar_agent --help
```

测试用固定数据和模型替身，不需要网络或 Key。真实采集用 crawl 单独验证。
真实模型端到端需要你配置提供商、模型和 Key，demo 不能替代这个验证。
如果网络超时或证书报错，先检查网络、代理和 Python 证书配置；不要关闭证书验证。
如果出现 401/404，核对 Key、基础地址、模型名；接口需要原生工具调用能力。

可继续完善：增加 GitHub/高校官网工具，个人条件配置，结果去重、定期更新，
再为来源准确性和需求判断建立小评测集。定时任务当前未创建。

协议参考：[Hacker News 官方 API](https://github.com/HackerNews/API)、
[Function calling](https://developers.openai.com/api/docs/guides/function-calling)。
