# DSH 实习信息助手

一个运行在 DeepSeek Harness（DSH）中的实习信息插件：帮助求职者发现岗位线索、核对招聘原文，并结合个人情况分析哪些机会值得进一步了解。

```text
用户需求 → DSH 搜索 → 插件整理候选、读取原文、校验证据 → DSH 解释结果
```

插件会尽量区分**原文事实、模型分析和未知信息**。候选链接不一定是有效岗位，“疑似在招”也不是招聘方的保证；投递前请打开原页面核实。

## 当前维护的部分

**以 [`dsh-internship/`](dsh-internship/) 为主要开发和发布入口。** 其中包含 DSH 工具注册、Python 桥接、候选管理、证据核验、档案读取和看板。

- [插件介绍、安装与使用](dsh-internship/README.md)
- [开发记录：为什么这样设计](dsh-internship/开发记录.md)

在 DSH 中，可以先尝试：

> 根据我的实习档案查找岗位，展示每条的原文依据和待确认问题。不要代我投递。

具体安装步骤请看插件说明。当前不支持自动投递、自动发邮件或定时日报；是否能读取网页取决于来源与页面形式。

## 仓库目录

```text
agent/
├── dsh-internship/          当前维护的 DSH 插件
├── internship_agent/        早期独立 Python Agent，保留参考
├── tests/                   独立 Agent 的历史测试
└── docs/                    历史说明
```

`internship_agent/` 是旧的独立入口，**不是插件运行时的依赖路径**。插件在 `dsh-internship/python/agent_snapshot/` 中保留了一份业务代码快照；它与旧 Agent 不会自动同步。修改、提交旧 Agent 不等于更新插件，反过来也一样。

旧 Agent 的说明保留在[历史文档](docs/independent-agent-archive.md)，其中可能涉及尚未发布或已变化的本地文件。旧文件保留供参考，不作为当前插件的安装说明。

## 本地数据和开发约定

- 插件默认将档案、数据库、网页快照和报告保存在 `~/.dsh/internship/`；独立 Agent 使用自己的数据目录，两者不自动同步。
- `.env`、密钥、用户档案、数据库及运行报告不应提交到 GitHub。仓库的忽略规则保留对这些文件的保护。
- 当前主要修改 `dsh-internship/`；准备提交时在 GitHub Desktop 中检查选中的文件，避免把独立 Agent 中未完成的本地改动一起提交。
- 更新 GitHub 源码不会自动更新已经安装到 DSH 的插件。重新安装或更新插件后，需要重新启动 DSH 并验证。

插件测试方法及功能边界见[详细说明](dsh-internship/README.md)。
