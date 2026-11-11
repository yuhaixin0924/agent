# DSH 实习信息助手

一个运行在 DeepSeek Harness（DSH）中的本地插件，帮助你**寻找实习线索、核对岗位原文，再结合个人情况分析是否值得进一步了解**。

想了解这个项目为什么这样设计，可以阅读 [我的开发记录](开发记录.md)。

例如，你可以告诉 DSH：

> 我是大二学生，想在广州找 Agent 或后端开发实习。请关注到岗时间、实习周期、远程和学习机会；岗位没有写清楚的地方请标为未知。

DSH 会根据你的要求使用搜索工具，插件则负责整理候选、保存网页和核对证据。搜索范围、网页可访问性和结果准确性都有局限，请在投递前查看招聘方原文。

## 能做什么？

| 功能 | 对你有什么帮助 |
| --- | --- |
| 中文档案表单 | 填写求职条件；从简历提取草稿，核对缺失项后保存到本机档案 |
| 查找实习线索 | 根据档案中的城市、关键词生成搜索计划；由 DSH 的搜索工具寻找链接 |
| 整理候选 | 过滤来源、合并重复链接，记录哪些页面尚未读或读取失败 |
| 阅读和保存原文 | 保存网页快照，便于之后回看岗位当时写了什么 |
| 校验证据 | 保存岗位分析时检查引用是否出现在已读原文中 |
| 结合个人情况分析 | 参考可到岗时间、实习时长和城市等条件，列出冲突和待确认事项 |
| 展示看板 | 查看候选列表、来源、读取情况，以及“疑似在招 / 已失效 / 状态未知” |

**当前不支持自动投递、自动发邮件或定时日报。** 看板里的“疑似在招”只是程序根据近期网页内容做出的判断，不代表招聘方确认仍在招。技术关键词不匹配也不应成为唯一的淘汰理由。

## 它是怎么工作的？

```text
你描述求职需求
       ↓
DSH + 大模型：理解需求，决定下一步调用什么工具
       ↓
DSH 的搜索工具：查找岗位链接
       ↓
本插件：整理链接 → 阅读网页 → 保存原文 → 校验证据
       ↓
本插件：读取个人档案，做初步规则匹配
       ↓
DSH + 大模型：解释岗位、冲突和需要向招聘方确认的问题
```

这里的**大模型负责理解和解释**，插件里的代码负责执行具体操作和检查。网页中找不到的信息应写“未知”；引用能在原文中找到，也不能保证模型的解释一定正确。

插件复用了本仓库原 Agent 的部分 Python 代码，但**它们使用各自的数据和代码副本**：插件不会自动读取原 Agent 的档案或数据库，修改原 Agent 也不会自动更新插件。

## 安装：macOS

以下适用于已安装 DeepSeek Harness 的用户。当前插件版本为 **0.2.0**，需要 Python 3.10 或更新版本；先在“终端”输入 `python3 --version` 检查。安装 DSH 的版本也可能影响兼容性。

### 第一步：下载代码

在终端依次执行：

```bash
cd ~/Desktop
git clone https://github.com/yuhaixin0924/agent.git
cd agent/dsh-internship
```

如果你已经下载过这个仓库，就不必再次 `clone`；只需用 `cd` 进入已有的 `agent/dsh-internship` 文件夹。没有 Git 的话，也可以在 [仓库页面](https://github.com/yuhaixin0924/agent) 选择 **Code → Download ZIP**，解压后进入其中的 `dsh-internship` 文件夹。

### 第二步：安装插件

**先完全退出 DSH**，然后在刚才的终端执行：

```bash
"/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh" plugin --profile desktop add "$PWD"
```

这里的 `$PWD` 表示终端当前所在的文件夹，也就是上一步进入的 `dsh-internship`。如果你的 DSH 不在“应用程序”文件夹，需要将命令开头的路径改成实际安装位置。

如果你已经把 `dsh` 命令加入终端 PATH，也可以用较短的命令：

```bash
dsh plugin --profile desktop add "$PWD"
```

### 第三步：重启并检查

打开 DSH，在新对话中发送：

> 调用 `internship_status`，检查实习插件是否正常工作。

如果返回结果包含 `"ok": true`，说明工具已加载。若找不到工具，检查插件是否启用，并确认已完全退出后重新打开 DSH。

Windows 浏览器版请使用下方的 `web` 配置，不要照搬桌面版的 `desktop`。

### 已安装旧版本？

先在本地仓库根目录运行 `git status`，确认没有需要保留的未提交改动，再运行 `git pull --ff-only origin main`。随后进入 `dsh-internship`，退出 DSH，重新执行上面的安装命令并启动 DSH。

升级不会自动重新检查旧岗位。打开新版报告后，旧记录可能显示“状态未知”；可以让 DSH 分批复检。

## 安装：Windows 浏览器版

2026-11-11 已在 Windows、DSH **0.1.0-rc.6**、Node.js 24、Python 3.11 的环境中完成本地链接安装，重启后显示“实习看板”入口。插件工具的本地测试通过；这不等于已经验证模型搜索和真实岗位分析的全部流程。

### 第一步：检查 Python

在 PowerShell 中运行：

```powershell
python --version
```

需要 Python 3.10 或更新版本。Windows 下插件默认调用 `python`；macOS/Linux 默认调用 `python3`。若 Harness 找不到 Python，可以在插件配置中把 `python` 设置为可执行文件的绝对路径，例如 `C:/Python311/python.exe`。

### 第二步：安装到 Web 配置

先停止运行 `dsh web` 的服务，再在 PowerShell 中执行（请按实际位置修改仓库路径）：

```powershell
dsh plugin --profile web add "E:/Github_program/agent/dsh-internship" --ignore-scripts
```

如果提示找不到 `dsh`，而你是通过 npm 全局安装的 Harness，可以使用：

```powershell
$dshCli = Join-Path $env:APPDATA 'npm/node_modules/@deepseek-ai/dsh/lib/bin.js'
node $dshCli plugin --profile web add "E:/Github_program/agent/dsh-internship" --ignore-scripts
node $dshCli web
```

若 `dsh` 已在 PATH 中，则用 `dsh web` 启动。打开终端显示的地址（本次为 `http://127.0.0.1:3080`），刷新已有页面。左侧应出现“实习看板”，新对话中可发送：

> 请只调用 `internship_status`，显示插件状态；暂不搜索或读取其他文件。

这是**链接到本地文件夹**的安装，移动或删除 `dsh-internship` 文件夹会影响加载。修改插件代码后需要重新加载或重启 Harness。插件已安装但旧进程尚未重启时，页面可能仍看不到工具。

### 第三步：准备个人档案

如果需要创建空档案，可以在 PowerShell 中执行：

```powershell
cd E:\Github_program\agent\dsh-internship
python -X utf8 python/bridge.py --data-dir "$env:USERPROFILE/.dsh/internship" --init-profile
notepad "$env:USERPROFILE/.dsh/internship/profile.json"
```

已有档案不会被初始化命令覆盖。字段格式见下文“填写个人档案”。默认数据目录为 `%USERPROFILE%/.dsh/internship`；设置过 `DSH_HOME` 或 `dataDir` 时以实际配置为准。首次使用时档案未配置、岗位数为 0 是正常状态；先生成候选报告，看板才会有内容。

## 开始使用

### 方式一：让 DSH 帮你找线索

安装后，在 DSH 中发送：

> 请先读取我的实习档案。根据我的城市和方向制定搜索计划，使用你已有的搜索工具查找实习岗位，优先阅读具体岗位详情。列出来源、主要工作、时间要求和需要确认的问题；不要把没写明的条件当成满足，也不要帮我投递。

如果档案还没填写，可以对 DSH 说“我要建立个人档案，请给我填写链接”。`internship_profile` 会返回表单地址和缺失字段，DSH 可据此引导填写或追问。也可以在对话中提出具体修改：DSH 应先用 `internship_profile_propose` 生成草稿、展示差异与疑问，用户确认这份草稿后再用 `internship_profile_apply` 保存。普通对话不会自动更新档案。

### 方式二：分析一条已有岗位链接

将下面的话和真实链接一起发给 DSH：

> 请阅读这个岗位页面，保存原文证据，并结合我的档案解释：岗位主要做什么、时间和地点是否合适、有哪些技术差距、哪些问题还要问招聘方。没有写明的内容标为未知。链接：在这里粘贴真实链接。

插件只能读取支持直接访问的公开网页。需要登录、验证码、JavaScript 渲染或 PDF 的页面可能无法读取；搜索摘要也不能代替岗位正文。

### 查看候选看板

在 DSH 中说：

> 请生成实习候选报告，并打开看板。

报告会生成 `candidates.html`、`candidates.json` 和 `candidates.txt`。在支持该插件客户端的 DSH 界面中，可通过侧栏的“实习看板”查看；如果没有看到入口，让 DSH 给出报告路径，或在浏览器中打开本地 HTML 文件。

看板展示的是**累计候选**，不是只包含今天新增岗位的日报。首次使用或尚未生成报告时，看板可能为空。

## 填写个人档案

档案是保存在自己电脑上的 JSON 文件；不填也可以读岗位，但搜索计划和匹配结果会缺少个性化条件。

### 推荐：中文表单与简历导入

浏览器版点击 **实习看板 → 个人档案**，也可以打开当前 Harness 地址下的 `/dsh-internship/profile.html`（本机示例：`http://127.0.0.1:3080/dsh-internship/profile.html`）。入口不依赖是否已生成候选报告。

1. 直接填写中文条目，或上传 PDF / DOCX / TXT / MD 简历（最大 4 MB；PDF 最多 10 页）。
2. 简历在本机提取文字，只按明确中文字段生成建议并填入空白项；不会覆盖已填内容，也不会自动保存。原文件与提取正文不写入档案。
3. 核对“已掌握 / 正在学习”、时间、城市等信息，按页面提示补充待定项。扫描图片、旧版 DOC 和复杂排版可能无法提取；当前没有 OCR，也没有模型自动理解整份简历的能力。
4. 点击“保存档案”先查看修改预览，确认条目拆分和条件后点击“确认并保存这些修改”，才写入 `profile.json`。下一次调用 `internship_profile` 或进行规则匹配时读取新内容。DSH 已经说出的旧结论不会自动重写，需要让它重新读取后分析。

当前所有实习对话共用一份档案，不会随会话切换人物。保存前会校验字段、检测版本冲突，原有档案保留为同目录的 `profile.json.bak`（仅保留上一份）。表单不调用模型、不自动向模型发送简历；后续岗位分析会使用相关档案内容。

多个条目支持逗号、顿号、分号和换行。常见、可明确识别的空格列表（如 `广州 深圳 杭州`、`Git Python HTML`）会在预览中拆分；`Agent 开发`、`Machine Learning` 等短语保留。无法确定的空格表达保留原文并提示核对。DSH 可以结合对话进一步理解，重新提交整理草稿，但仍须用户确认；规则本身没有通用语义理解能力。

“每周可出勤上限”填 5 表示每周最多可提供 5 天，满足岗位最低要求为 3、4 或 5 天的出勤条件，不是只接受正好 5 天。只有设为硬约束且岗位已核实的最低要求超过此数时，才因此排除。纠正解释但数值不变时，工具会返回“无字段变化”，不会虚报修改。

对话修改和表单共用字段校验、版本检查及跨进程保存锁。工具只可修改档案白名单字段，不能指定任意文件路径。草稿绑定原档案版本，有效期 24 小时，一次应用后不能重复使用；修改后会从磁盘重读并返回实际差异。`user_confirmed` 是工具调用时对已取得用户确认的声明，插件无法独立验证聊天里是否真的取得了用户同意，DSH 必须遵守工具说明；希望由界面确认时可打开草稿的 `review_url`，点击确认保存。

需要撤销时，可点击表单“恢复上一版”并核对预览；也可告诉 DSH“撤销上一轮档案修改”，由它调用 `internship_profile_propose`（`restore_previous=yes`），在用户确认后应用恢复草稿。恢复动作同样检查版本。此处仅保留上一份备份，不是完整的历史版本管理。

“其他重要条件或不可接受的情况”可自由补充交通、周边设施、工作方式等要求，保存在 `additional_constraints`。建议注明“必须”或“希望”。这些文字提供给后续分析作参考；当前没有地图或距离核验能力，缺乏证据时应记为待确认，不参与现有规则的自动排除。

DOCX / TXT / MD 无需额外 Python 库。PDF 需在插件目录安装可选依赖（本机已安装并验证 pypdf 6.21.4）：

```powershell
python -m pip install --target .runtime/python -r requirements-resume.txt
```

macOS/Linux 将 `python` 换成 `python3`。依赖目录 `.runtime/` 不提交到仓库；其他机器需单独安装。文字提取成功不代表字段提取完整，请以页面确认内容为准。

### 也可直接编辑 JSON

在插件目录运行（macOS 示例）：

```bash
python3 python/bridge.py --data-dir "$HOME/.dsh/internship" --init-profile
open -e "$HOME/.dsh/internship/profile.json"
```

第一行创建空档案，第二行用文本编辑器打开。**已有档案不会被初始化命令覆盖**；如果提示文件已存在，直接运行第二行打开即可。上面的路径适用于默认配置；若设置过 `DSH_HOME` 或插件 `dataDir`，请改为实际的数据目录。

示例（只是说明格式，请按自己的真实情况填写）：

```json
{
  "stage": "大二",
  "skills_known": ["C++"],
  "skills_learning": ["Python", "Agent 开发"],
  "cities": ["广州"],
  "keywords": ["Agent", "后端"],
  "days_per_week": null,
  "months": null,
  "hard_constraints": [],
  "priorities": ["实习时间", "学习机会"]
}
```

`null` 表示尚不清楚，不是 0。`skills_known` 是已经掌握的技能，`skills_learning` 是正在学习的技能。只有明确不能妥协时，才在 `hard_constraints` 中填写 `"days_per_week"`、`"months"` 或 `"city"`；不确定就留空。城市和出勤等规则仍可能误判，请核对原文。

默认数据目录是 `~/.dsh/internship/`，包含档案、数据库、网页快照和报告。它们属于个人运行数据，不应提交到 GitHub。DSH 分析时会将相关档案和岗位内容交给所配置的模型服务；使用 DSH 的搜索或模型可能产生服务费用，插件自身不调用模型。

## 常见问题

**为什么搜索计划出来了，却没有岗位？**

`internship_candidates_plan` 只生成查询词，真正的搜索由 DSH 的搜索工具执行。需要让 DSH 搜索后把结果加入候选队列；搜索失败、白名单限制或没有合适结果时，也可能没有候选。

**为什么岗位显示“状态未知”？**

可能是网页读取失败、旧记录没有可靠的成功检查标记，或者信息不足。可以让 DSH 调用 `internship_candidates_recheck` 分批复检；即便显示“疑似在招”，投递前仍需核实。

**提示找不到 Python 怎么办？**

Windows 先确认 `python --version` 能运行；macOS/Linux 使用 `python3 --version`。如果 DSH 仍找不到，可在插件配置中把 `python` 设为 Python 可执行文件的绝对路径。

**如何看到结果为什么被推荐？**

请 DSH 展示原文引用、结合档案的分析和未确认信息。关键词命中只是一项简单统计，不是录取概率，也不是综合匹配度。

## 给开发者

| 文件 | 作用 |
| --- | --- |
| `src/index.js` | 向 DSH 注册工具，通过子进程调用 Python |
| `schemas.json` | 定义工具接收的参数 |
| `python/bridge.py` | 分发工具请求、处理档案和岗位证据 |
| `python/candidates.py` | 候选队列、页面筛查、复检和看板 |
| `python/agent_snapshot/` | 从原 Agent 复制的 Python 代码快照 |
| `client.js` | 支持时向 DSH 客户端添加看板入口 |
| `cordis.patch.yml` | DSH 插件挂载声明 |

主要工具分两组：`internship_candidates_plan / add / check / recheck / report / view` 负责发现和管理线索；`internship_profile / profile_propose / profile_apply / read_page / read_snapshot / record / list / get / status` 负责档案、证据与岗位。`plan` 可以选择 `baseline` 固定查询或默认的 `profile` 画像查询，并通过 `extra_queries` 登记补充查询；插件接收 DSH 提交的 URL，不能独立证明搜索过程。

在插件目录运行测试：

```bash
npm test
```

测试使用临时目录和模拟网页，不调用模型或搜索服务。现有来源白名单、页面分类和时效判断都是有限的规则；本项目尚需通过人工标注的真实岗位样本评估实际效果。
