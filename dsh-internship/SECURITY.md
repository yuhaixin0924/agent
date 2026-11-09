# 安全说明

## 仓库里不会出现的东西

- `.env`、`*.env`、任何 API key、账号密码、Cookie、私钥
- `state.sqlite3` 数据库、`profile.json` 个人档案
- 网页快照、抓取日志、运行报告（`candidates.json` / `candidates.html` / `sources.json`）
- `node_modules/`、`__pycache__/`、`*.pyc`、`*.tgz`
- 本机绝对路径与用户名（README 中已替换为 `/path/to/...`）

插件运行时把数据放在 `${DSH_HOME:-~/.dsh}/internship/`，这个目录**不在仓库内**，也不应复制进来。

## 如果你要报告安全问题

请开 issue 描述影响面，不要贴真实密钥或他人个人信息。

## 如果你曾经误提交密钥

删除文件或改写提交都不够：**先到服务商吊销并换新**，再清理历史（`git filter-repo`），最后强制推送并通知协作者重新克隆。
