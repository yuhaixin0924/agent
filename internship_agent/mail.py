"""发送能力与模型隔离；人工审核内容绑定到附件快照。"""
import hashlib
import json
import os
import re
import smtplib
import ssl
import uuid
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

from .core import digest, encode, now


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r"[^\s@<>,;\r\n]+@[^\s@<>,;\r\n]+\.[^\s@<>,;\r\n]+", value):
        raise ValueError("请提供单个纯邮箱地址，不含显示名、换行或多个收件人。")
    return value


def config(root):
    path = Path(root) / "mail.env"
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip("\"'")
    keys = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_SECURITY", "DAILY_TO")
    return {k: os.environ.get(k, values.get(k, "")) for k in keys}


def create(store, kind, recipient, subject, body, *, attachment=None, job=None, versions=None):
    address(recipient)
    if kind not in {"application", "digest"} or not subject or any(c in subject for c in "\r\n"):
        raise ValueError("无效邮件类型或主题。")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("邮件正文不可为空。")
    raw = None
    name = ""
    if attachment:
        path = Path(attachment)
        if path.suffix.lower() != ".pdf" or path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("简历附件只支持不超过 10 MB 的 PDF。")
        raw = path.read_bytes()
        if not raw.startswith(b"%PDF-"):
            raise ValueError("附件没有 PDF 文件头。")
        name = path.name
    if kind == "application" and (not raw or not job):
        raise ValueError("投递邮件需要关联岗位和 PDF 简历。")
    data = {"to": recipient, "subject": subject, "body": body, "attachment_name": name,
            "attachment_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
            "job": job, "versions": versions or {}, "from": address(config(store.root)["SMTP_FROM"])}
    mail_id = uuid.uuid4().hex[:16]
    with store.db:
        store.db.execute("INSERT INTO mail VALUES (?,?,?,?,?,?)",
                         (mail_id, kind, encode(data), raw, "draft", now()))
    return mail_id


def get(store, mail_id):
    row = store.db.execute("SELECT * FROM mail WHERE id=?", (mail_id,)).fetchone()
    if row is None:
        raise ValueError("邮件 ID 不存在。")
    return row, json.loads(row["data"])


def fingerprint(data):
    return digest(data)


def message(mail_id, data, raw):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = data["from"], data["to"], data["subject"]
    msg["Message-ID"] = f"<{mail_id}@internship-radar.local>"
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(data["body"])
    if raw:
        msg.add_attachment(raw, maintype="application", subtype="pdf", filename=data["attachment_name"])
    return msg


def export(store, mail_id):
    row, data = get(store, mail_id)
    folder = store.root / "review" / mail_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    (folder / "mail.eml").write_bytes(message(mail_id, data, row["attachment"]).as_bytes())
    (folder / "draft.json").write_text(encode(data), encoding="utf-8")
    if row["attachment"]:
        (folder / "resume.pdf").write_bytes(row["attachment"])
    return folder


def revise(store, mail_id, values, attachment=None):
    row, data = get(store, mail_id)
    if row["state"] != "draft" or row["kind"] != "application":
        raise ValueError("只允许修改未发送的投递草稿。")
    allowed = {"to", "subject", "body"}
    # export 的 draft.json 可原样编辑；元数据不能变更。
    for key, value in values.items():
        if key not in allowed and value != data.get(key):
            raise ValueError("只能编辑 to / subject / body；附件请用 --resume 替换。")
    new = {**data, **{k: v for k, v in values.items() if k in allowed}}
    address(new["to"])
    if not isinstance(new["subject"], str) or not new["subject"] or any(c in new["subject"] for c in "\r\n"):
        raise ValueError("主题无效。")
    if not isinstance(new["body"], str) or not new["body"].strip():
        raise ValueError("正文无效。")
    raw = row["attachment"]
    if attachment:
        path = Path(attachment)
        if path.suffix.lower() != ".pdf" or path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("简历必须是不超过 10 MB 的 PDF。")
        raw = path.read_bytes()
        if not raw.startswith(b"%PDF-"):
            raise ValueError("附件不是 PDF。")
        new["attachment_name"] = path.name
        new["attachment_sha256"] = hashlib.sha256(raw).hexdigest()
    with store.db:
        result = store.db.execute("UPDATE mail SET data=?, attachment=? WHERE id=? AND state='draft' AND data=?",
                                 (encode(new), raw, mail_id, row["data"]))
        if result.rowcount != 1:
            raise ValueError("草稿已被其他进程修改，请重新查看。")


def smtp_send(cfg, msg):
    port = int(cfg["SMTP_PORT"] or ("465" if cfg["SMTP_SECURITY"] == "ssl" else "587"))
    context = ssl.create_default_context()
    if cfg["SMTP_SECURITY"] == "ssl":
        connection = smtplib.SMTP_SSL(cfg["SMTP_HOST"], port, timeout=30, context=context)
    elif cfg["SMTP_SECURITY"] == "starttls":
        connection = smtplib.SMTP(cfg["SMTP_HOST"], port, timeout=30)
    else:
        raise ValueError("SMTP_SECURITY 只能为 ssl 或 starttls，不支持明文发送。")
    try:
        if cfg["SMTP_SECURITY"] == "starttls":
            connection.ehlo()
            connection.starttls(context=context)
            connection.ehlo()
        connection.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        refused = connection.send_message(msg)
        if refused:
            raise RuntimeError("收件人被服务器拒绝。")
    finally:
        # close 不发送 QUIT，避免已成功发送却因 QUIT 超时报错。
        connection.close()


def send(store, mail_id, *, approval=None, daily=False, transport=smtp_send):
    cfg = config(store.root)
    row, data = get(store, mail_id)
    if daily:
        if row["kind"] != "digest" or data["to"] != address(cfg["DAILY_TO"]):
            raise ValueError("自动发送仅允许发给 DAILY_TO 的日报。")
    elif approval != fingerprint(data):
        raise ValueError("必须确认当前邮件和附件版本。")
    if data["from"] != address(cfg["SMTP_FROM"]):
        raise ValueError("发件配置已变化，请重新生成草稿。")
    if not all(cfg[k] for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD")):
        raise ValueError("SMTP 配置不完整。")
    if cfg["SMTP_SECURITY"] not in {"ssl", "starttls"}:
        raise ValueError("SMTP_SECURITY 只能为 ssl 或 starttls。")
    int(cfg["SMTP_PORT"] or "465")
    # 在连接 SMTP 前持久化占位，防止重启或并发操作重复投递。
    with store.db:
        store.db.execute("BEGIN IMMEDIATE")
        if daily:
            pending = store.db.execute("SELECT id FROM mail WHERE kind='digest' AND state IN ('sending','uncertain')").fetchone()
            if pending:
                raise ValueError("存在结果待核对的日报，先人工核对，不能自动重发。")
            known = dict(store.db.execute("SELECT job_id, hash FROM delivered WHERE recipient=?", (data["to"],)))
            if data["versions"] and all(known.get(k) == v for k, v in data["versions"].items()):
                raise ValueError("这些岗位版本已通知，不重复发送。")
        changed = store.db.execute("UPDATE mail SET state='sending' WHERE id=? AND state='draft' AND data=?",
                                   (mail_id, row["data"]))
        if changed.rowcount != 1:
            raise ValueError("邮件已发送、发送中或版本改变；不能重复发送。")
    try:
        transport(cfg, message(mail_id, data, row["attachment"]))
    except Exception:
        with store.db:
            store.db.execute("UPDATE mail SET state='uncertain' WHERE id=?", (mail_id,))
        raise ValueError("发送结果待核对：请检查发件箱和收件箱，不自动重试。") from None
    mark_sent(store, mail_id)


def mark_sent(store, mail_id):
    row, data = get(store, mail_id)
    with store.db:
        store.db.execute("UPDATE mail SET state='sent' WHERE id=?", (mail_id,))
        if row["kind"] == "digest":
            for job_id, version in data["versions"].items():
                store.db.execute("INSERT INTO delivered VALUES (?,?,?) ON CONFLICT(recipient,job_id) DO UPDATE SET hash=excluded.hash",
                                 (data["to"], job_id, version))


def reconcile(store, mail_id, outcome):
    row, _ = get(store, mail_id)
    if row["state"] not in {"uncertain", "sending"}:
        raise ValueError("只能核对 sending / uncertain 状态。")
    if outcome == "sent":
        mark_sent(store, mail_id)
    else:
        with store.db:
            store.db.execute("UPDATE mail SET state='cancelled' WHERE id=?", (mail_id,))
    store.event("reconcile", {"id": mail_id, "outcome": outcome})
