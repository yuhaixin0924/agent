"""运行 python3 -m radar_agent --help 查看入口。"""

import argparse
import json
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone

from .agent import Agent
from .demo import DemoClient, fixture_fetch
from .http import NetworkError
from .llm import ChatClient, ROOT
from .tools import FEEDS, HackerNewsTools

DEFAULT_TASK = "找出适合我的 Agent 开发学习资料和开发者需求线索。若有实习或竞赛机会，也单独列出；没有就说明。"


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="轻量个人信息雷达（Python 标准库，无需 pip 安装）")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="离线固定样例：不联网、不调用模型、不需要 Key")
    crawl = commands.add_parser("crawl", help="真实 HN 采集：不调用模型，不需要 Key")
    crawl.add_argument("--feed", choices=sorted(FEEDS), default="new")
    crawl.add_argument("--limit", type=int, choices=range(1, 21), default=5, metavar="1-20")
    run = commands.add_parser("run", help="真实模型 Agent：需要配置 .env")
    run.add_argument("task", nargs="?", default=DEFAULT_TASK)
    run.add_argument("--max-steps", type=int, choices=range(1, 13), default=6, metavar="1-12")
    for sub in (demo, crawl, run):
        sub.add_argument("--output-dir", type=Path, default=ROOT / "runs")
    args = parser.parse_args()

    # 配置不完整时先退出，避免创建空运行目录。
    try:
        client = ChatClient.from_env() if args.command == "run" else DemoClient()
    except ValueError as error:
        print(f"配置错误：{error}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = Path(tempfile.mkdtemp(prefix=f"{stamp}_{args.command}_", dir=args.output_dir))
    agent = None
    with (folder / "events.jsonl").open("w", encoding="utf-8") as log:
        def emit(event):
            log.write(json.dumps(event, ensure_ascii=False) + "\n")
            log.flush()
            if event["event"] == "model_start":
                print(f"模型第 {event['step']} 轮…", flush=True)
            elif event["event"] == "tool_start":
                print(f"调用 {event['tool']}：{event['arguments']}", flush=True)

        try:
            if args.command == "crawl":
                data = HackerNewsTools().get_posts(feed=args.feed, limit=args.limit)
                save_json(folder / "posts.json", data)
                for post in data["posts"]:
                    print(f"- {post['title']}\n  {post['discussion_url']}")
                if not data["posts"]:
                    raise ValueError("这批帖子没有有效记录；详情见 posts.json。")
                result = {"status": "partial" if data["errors"] else "completed",
                          "answer": f"采集 {len(data['posts'])} 条，失败 {len(data['errors'])} 条。"}
            else:
                is_demo = args.command == "demo"
                if is_demo:
                    print("离线演示：使用固定数据和脚本化模型替身，不是真实推理。")
                tools = HackerNewsTools(fixture_fetch) if is_demo else HackerNewsTools()
                agent = Agent(client, tools, max_steps=6 if is_demo else args.max_steps, emit=emit)
                result = agent.run(DEFAULT_TASK if is_demo else args.task)
        except (NetworkError, ValueError, OSError) as error:
            result = {"status": "error", "answer": str(error)}
        finally:
            if agent is not None:
                save_json(folder / "messages.json", agent.messages)

    save_json(folder / "result.json", result)
    (folder / "report.md").write_text(result["answer"] + "\n", encoding="utf-8")
    print(f"\n{result['answer']}\n\n状态：{result['status']}\n结果目录：{folder}")
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
