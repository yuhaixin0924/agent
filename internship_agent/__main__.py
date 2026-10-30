"""python3 -m internship_agent --help"""
import argparse
import json
import os
from pathlib import Path
import sys

from .llm import ChatClient, ROOT
from .core import Store, encode, read_json, ranked, sync
from . import mail
from .research import research, render_cards


def write_new(path, text):
    with path.open("x", encoding="utf-8") as f:
        f.write(text)
    path.chmod(0o600)


def init(root):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    profile = {"stage": "", "background": "", "cities": [], "keywords": [],
               "skills_known": [], "skills_learning": [], "growth_goal": "",
               "priorities": ["period", "attendance", "remote", "learning", "intensity", "conversion"],
               "available_period": {"start_date": None, "end_date": None, "preference": ""},
               "days_per_week": None, "months": None, "hard_constraints": [],
               "accepted_degree_labels": []}
    configs = {"profile.json": json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
               "sources.json": "[]\n",
               "mail.env": "SMTP_HOST=\nSMTP_PORT=465\nSMTP_SECURITY=ssl\nSMTP_USER=\nSMTP_PASSWORD=\nSMTP_FROM=\nDAILY_TO=\n"}
    for target, content in configs.items():
        if not (root / target).exists():
            write_new(root / target, content)
    print(f"配置目录：{root}\n先修改 profile.json 和 sources.json；邮箱是可选扩展，已有文件不覆盖。")


def report(store, profile, *, selected=None, only_new=False):
    cfg = mail.config(store.root)
    known = dict(store.db.execute("SELECT job_id, hash FROM delivered WHERE recipient=?", (cfg["DAILY_TO"],)))
    lines, versions = ["实习岗位清单（推荐不等于符合全部资格；请查看原文）", ""], {}
    results = ranked(store.jobs(), profile)
    if selected is not None:
        order = {r["id"]: i for i, r in enumerate(selected)}
        results = sorted((r for r in results if r["id"] in order), key=lambda r: order[r["id"]])
    for result in results:
        job = result["job"]
        if result["status"] == "excluded" or (only_new and known.get(job["id"]) == job["version"]):
            continue
        versions[job["id"]] = job["version"]
        lines += [f"[{job['id']}] {job['title']} | {job['company']}", job["url"],
                  "地点：" + (job["city"] or "未知"), "关键词：" + ", ".join(result["keywords"]),
                  "待核对：" + "；".join(result["unknown"]), "最近采集：" + job["last_seen"]]
        if selected is not None:
            item = selected[order[job["id"]]]
            lines += ["模型建议（待审核）：" + item["reason"], "原文引用：" + item["quote"]]
        lines.append("")
        if len(versions) >= 20:
            break
    if not versions:
        lines.append("本次没有符合筛选条件的新结果；这不代表全网没有岗位。")
    return "\n".join(lines), versions


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description="实习检索、日报与人工确认投递（标准库版）")
    p.add_argument("--data-dir", type=Path, default=ROOT / "internship_data")
    subs = p.add_subparsers(dest="cmd", required=True)
    subs.add_parser("init", help="创建本地配置，不覆盖已有内容")
    imp = subs.add_parser("import", help="导入岗位 JSON")
    imp.add_argument("path", type=Path)
    subs.add_parser("sync", help="按 sources.json 采集")
    for command in ("report", "daily"):
        sub = subs.add_parser(command, help="生成岗位报告" if command == "report" else "采集后生成新增岗位日报")
        sub.add_argument("--ai", action="store_true", help="调用配置的模型，产生费用；画像和岗位文本会发给提供商")
        sub.add_argument("--profile", type=Path, help="指定另一个用户画像 JSON，默认使用本地 profile.json")
        sub.add_argument("--job-id", help="只分析指定岗位，须同时使用 --ai")
        if command == "daily":
            sub.add_argument("--send", action="store_true", help="实际发送给 DAILY_TO，仅用于给自己发日报")
    draft = subs.add_parser("draft", help="为岗位生成待审核投递草稿")
    draft.add_argument("job_id")
    draft.add_argument("--to", required=True, help="人工核实的招聘邮箱")
    draft.add_argument("--resume", type=Path, required=True)
    draft.add_argument("--body", type=Path, help="使用本人撰写的 UTF-8 正文；否则使用不虚构经历的模板")
    for command in ("review", "send"):
        sub = subs.add_parser(command, help="导出并查看草稿" if command == "review" else "交互式确认后发送，禁止非交互投递")
        sub.add_argument("id")
    edit = subs.add_parser("edit", help="修改草稿；发送时必须重新确认")
    edit.add_argument("id")
    edit.add_argument("--file", type=Path, required=True, help="含 to、subject、body 的 JSON 或导出的 draft.json")
    edit.add_argument("--resume", type=Path)
    subs.add_parser("outbox", help="列出草稿与投递状态")
    evaluation = subs.add_parser("evaluate", help="固定岗位池上比较规则与可选模型 Agent")
    evaluation.add_argument("--labels", type=Path, required=True)
    evaluation.add_argument("--ai", action="store_true", help="旧排序评测已停用AI比较；使用规则基线或人工审阅机会证据卡")
    schedule = subs.add_parser("schedule-template", help="生成 macOS 每日调度文件，不安装、不启动")
    schedule.add_argument("--hour", type=int, choices=range(24), default=8)
    schedule.add_argument("--minute", type=int, choices=range(60), default=30)
    schedule.add_argument("--send", action="store_true", help="生成的任务会给 DAILY_TO 发日报；不含招聘投递")
    rec = subs.add_parser("reconcile", help="人工检查邮箱后，登记不确定发送的真实结果")
    rec.add_argument("id")
    rec.add_argument("--outcome", choices=("sent", "not-sent"), required=True)
    args = p.parse_args()
    try:
        if args.cmd == "init":
            init(args.data_dir)
            return 0
        if args.cmd == "schedule-template":
            from .schedule import template
            print("仅生成配置，尚未启用：", template(args.data_dir, args.hour, args.minute, args.send))
            return 0
        store = Store(args.data_dir)
        if args.cmd == "import":
            print(encode(store.ingest(read_json(args.path), "manual")))
        elif args.cmd in {"sync", "daily"}:
            sources = read_json(args.data_dir / "sources.json")
            if not isinstance(sources, list) or not sources:
                raise ValueError("sources.json 尚未配置真实来源。可先 import 岗位并运行 report。")
            results = sync(store, sources)
            print(encode(results))
            if any(not r["ok"] for r in results):
                raise ValueError("部分采集失败，已保存成功来源；本次停止日报发送，避免把失败当作无新岗位。")
        if args.cmd in {"report", "daily"}:
            profile = read_json(args.profile or args.data_dir / "profile.json")
            if args.job_id and not args.ai:
                raise ValueError("--job-id 与 --ai 一起使用。")
            if args.ai:
                analysis = research(store, profile, ChatClient.from_env(), job_id=args.job_id)
                (args.data_dir / "latest-assessment.json").write_text(encode(analysis), encoding="utf-8")
                cards = analysis["cards"]
                if args.cmd == "daily":
                    recipient = mail.config(store.root)["DAILY_TO"]
                    known = dict(store.db.execute("SELECT job_id,hash FROM delivered WHERE recipient=?", (recipient,)))
                    cards = [c for c in cards if known.get(c["id"]) != c["job_version"]]
                text = render_cards(cards, profile.get("priorities"))
                versions = {c["id"]: c["job_version"] for c in cards}
            else:
                text, versions = report(store, profile, only_new=args.cmd == "daily")
            (args.data_dir / "latest-report.txt").write_text(text, encoding="utf-8")
            print(text)
            if args.cmd == "daily" and versions:
                cfg = mail.config(args.data_dir)
                mail_id = mail.create(store, "digest", cfg["DAILY_TO"], "实习岗位日报：新增与更新", text, versions=versions)
                print("日报草稿：", mail_id)
                if args.send:
                    mail.send(store, mail_id, daily=True)
                    print("日报已交给 SMTP 服务器；实际到达仍以收件箱为准。")
        elif args.cmd == "draft":
            job = next((j for j in store.jobs() if j["id"] == args.job_id), None)
            if not job:
                raise ValueError("岗位不存在，请先 report 查询 ID。")
            body = args.body.read_text(encoding="utf-8") if args.body else (
                f"您好！\n\n我希望申请贵公司的 {job['title']} 岗位。随信附上个人简历，敬请审阅。"
                f"\n\n岗位来源：{job['url']}\n\n感谢您的时间。")
            mail_id = mail.create(store, "application", args.to, "实习申请：" + job["title"], body,
                                  attachment=args.resume, job={"id": job["id"], "url": job["url"], "version": job["version"]})
            print("投递草稿：", mail_id, "\n审核目录：", mail.export(store, mail_id))
        elif args.cmd in {"review", "send"}:
            row, data = mail.get(store, args.id)
            print("状态：", row["state"], "\n审核目录：", mail.export(store, args.id))
            # JSON 转义终端控制字符，防止正文伪造终端提示。
            print(json.dumps(data, ensure_ascii=False, indent=2))
            if args.cmd == "send":
                if not sys.stdin.isatty():
                    raise ValueError("投递必须在交互终端中由本人确认，不接受管道或 --yes。")
                token = mail.fingerprint(data)
                expected = f"SEND {args.id} {token[:12]}"
                answer = input("请打开审核目录核对简历、收件人、正文和岗位。\n确认发送请输入：" + expected + "\n> ")
                if answer != expected:
                    raise ValueError("未确认，未发送。")
                mail.send(store, args.id, approval=token, daily=row["kind"] == "digest")
                print("已交给 SMTP 服务器；不会自动再次发送。")
        elif args.cmd == "edit":
            mail.revise(store, args.id, read_json(args.file), args.resume)
            print("草稿已更新，旧版本确认失效。审核目录：", mail.export(store, args.id))
        elif args.cmd == "outbox":
            for row in store.db.execute("SELECT id,kind,state,created FROM mail ORDER BY created DESC"):
                print(encode(dict(row)))
        elif args.cmd == "evaluate":
            from .evaluate import evaluate
            if args.ai:
                raise ValueError("机会评估已不输出匹配排名，旧 NDCG 对照不再适用。请去掉 --ai 查看规则基线，并按 OPPORTUNITY_PLAN.md 评测事实准确性。")
            result = evaluate(store, read_json(args.labels))
            (args.data_dir / "evaluation.json").write_text(encode(result), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.cmd == "reconcile":
            if not sys.stdin.isatty() or input("已人工核对邮箱？输入 CHECKED：") != "CHECKED":
                raise ValueError("未确认核对结果。")
            mail.reconcile(store, args.id, args.outcome)
            print("核对结果已记录；not-sent 会取消旧邮件，不会自动重试。")
        store.db.close()
        return 0
    except KeyboardInterrupt:
        print("已中断。若中断发生在发送中，请用 outbox 查看并人工核对。", file=sys.stderr)
        return 1
    except Exception as error:
        # 网络/SMTP 异常正文可能含收件人、服务器内容，不直接打印。
        detail = str(error) if isinstance(error, ValueError) else type(error).__name__
        print("操作未完成：" + detail, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
