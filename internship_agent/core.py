"""数据、采集与可解释的规则基线。仅依赖标准库。"""
import hashlib
import html
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
import xml.etree.ElementTree as ET

from .http import NoRedirect, request_json


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def plain(text):
    return re.sub(r"<[^>]+>", " ", html.unescape(str(text or ""))).strip()


def web_url(value):
    p = urlsplit(value)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("岗位来源链接必须是无凭据的 HTTP(S) 地址。")
    return value


def normalize(row, source):
    if not isinstance(row, dict):
        raise ValueError("每条岗位必须是对象。")
    result = {}
    for field in ("title", "company", "url", "description", "city", "degree", "deadline"):
        value = row.get(field, "")
        if not isinstance(value, str) or len(value) > 100000:
            raise ValueError(f"{field} 必须是字符串，且不超过 100000 字符。")
        result[field] = value.strip()
    if not result["title"] or not result["description"]:
        raise ValueError("岗位必须有 title 和 description，不能用空描述进行匹配。")
    web_url(result["url"])
    result["source"] = source
    result["id"] = hashlib.sha256(result["url"].encode()).hexdigest()[:16]
    for field in ("min_days", "min_months"):
        value = row.get(field)
        if value is not None and (type(value) is not int or value < 0 or value > 120):
            raise ValueError(f"{field} 应为非负整数或 null。")
        result[field] = value
    if result["deadline"]:
        datetime.strptime(result["deadline"], "%Y-%m-%d")
    return result


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.root / "state.sqlite3", timeout=20)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, data TEXT NOT NULL, hash TEXT NOT NULL,
          first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS mail (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL,
          attachment BLOB, state TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS delivered (
          recipient TEXT NOT NULL, job_id TEXT NOT NULL, hash TEXT NOT NULL,
          PRIMARY KEY(recipient, job_id));
        CREATE TABLE IF NOT EXISTS events (
          time TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL);
        """)
        (self.root / "state.sqlite3").chmod(0o600)

    def event(self, kind, data):
        with self.db:
            self.db.execute("INSERT INTO events VALUES (?,?,?)", (now(), kind, encode(data)))

    def ingest(self, rows, source):
        # 整批校验后写入，坏数据不会只导入一半。
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError("岗位输入必须是最多 10000 条的数组。")
        jobs = [normalize(row, source) for row in rows]
        added = changed = 0
        with self.db:
            for job in jobs:
                old = self.db.execute("SELECT hash FROM jobs WHERE id=?", (job["id"],)).fetchone()
                h = digest(job)
                added += old is None
                changed += old is not None and old["hash"] != h
                self.db.execute("""INSERT INTO jobs VALUES (?,?,?,?,?)
                  ON CONFLICT(id) DO UPDATE SET data=excluded.data, hash=excluded.hash,
                  last_seen=excluded.last_seen""", (job["id"], encode(job), h, now(), now()))
        return {"read": len(jobs), "new": added, "updated": changed}

    def jobs(self):
        return [dict(json.loads(r["data"]), first_seen=r["first_seen"],
                     last_seen=r["last_seen"], version=r["hash"])
                for r in self.db.execute("SELECT * FROM jobs ORDER BY last_seen DESC, id")]


def collect(source):
    """来源配置由用户提供，不接受模型生成的 URL。"""
    kind = source["type"]
    if kind == "json":
        return read_json(source["path"])
    if kind == "greenhouse":
        board = source["board"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", board):
            raise ValueError("无效的 Greenhouse board token。")
        data = request_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true", max_bytes=10_000_000)
        return [{"title": j["title"], "company": source.get("name", board),
                 "url": j["absolute_url"], "description": plain(j["content"]),
                 "city": j.get("location", {}).get("name", "")}
                for j in data["jobs"]
                if re.search(r"实习|\bintern(?:ship)?\b", j["title"], re.I)]
    if kind == "rss":
        url = web_url(source["url"])
        if not url.startswith("https://"):
            raise ValueError("RSS 采集只接受 HTTPS 地址。")
        with build_opener(NoRedirect()).open(Request(url, headers={"User-Agent": "InternshipRadar/1.0"}),
                                            timeout=20) as response:
            raw = response.read(2000001)
        if len(raw) > 2000000 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("RSS 超过大小限制或包含不支持的 XML 声明。")
        root = ET.fromstring(raw)
        rows = []
        atom = "{http://www.w3.org/2005/Atom}"
        for item in list(root.findall(".//item")) + list(root.findall(f"{atom}entry")):
            title = item.findtext("title") or item.findtext(f"{atom}title") or ""
            link = item.findtext("link")
            if not link:
                link = next((n.get("href") for n in item.findall(f"{atom}link")
                             if n.get("rel", "alternate") == "alternate"), "")
            body = item.findtext("description") or item.findtext(f"{atom}content") or item.findtext(f"{atom}summary") or ""
            if re.search(r"实习|\bintern(?:ship)?\b", title, re.I):
                rows.append({"title": title, "url": link, "description": plain(body),
                             "company": source.get("name", "")})
        return rows
    raise ValueError("来源只支持 json / rss / greenhouse。")


def sync(store, sources):
    results = []
    for source in sources:
        name = source.get("name", source.get("type", "unknown"))
        try:
            result = {"source": name, "ok": True, **store.ingest(collect(source), name)}
        except Exception as error:
            # 不输出带身份信息的地址或第三方响应。
            result = {"source": name, "ok": False, "error": type(error).__name__}
        store.event("collect", result)
        results.append(result)
    return results


def match(job, profile):
    rejected, unknown = [], []
    cities = profile.get("cities", [])
    if cities:
        if not job["city"]:
            unknown.append("地点未注明")
        elif not any(city.casefold() in job["city"].casefold() for city in cities):
            unknown.append("地点与偏好不一致，需核对城市别名、远程或异地可能性")
    for field, personal, label in (("min_days", "days_per_week", "每周出勤"),
                                    ("min_months", "months", "实习时长")):
        requirement, available = job.get(field), profile.get(personal)
        if requirement is None or available is None:
            unknown.append(f"{label}待确认")
        elif available < requirement:
            target = rejected if personal in profile.get("hard_constraints", ["days_per_week", "months"]) else unknown
            target.append(f"{label}不足：岗位要求 {requirement}，本人 {available}")
    if job.get("degree"):
        if job["degree"] not in profile.get("accepted_degree_labels", []):
            unknown.append("学历要求需人工核对：" + job["degree"])
    else:
        unknown.append("学历/年级要求待确认")
    if job.get("deadline"):
        if job["deadline"] < datetime.now().astimezone().date().isoformat():
            rejected.append("已过截止日期")
    else:
        unknown.append("截止日期及在招状态待确认")
    text = (job["title"] + " " + job["description"]).casefold()
    keywords = [k for k in profile.get("keywords", []) if k.casefold() in text]
    return {"id": job["id"], "score": len(keywords), "keywords": keywords,
            "status": "excluded" if rejected else "review" if unknown else "matched",
            "rejected": rejected, "unknown": unknown}


def ranked(jobs, profile):
    results = [dict(match(j, profile), job=j) for j in jobs]
    return sorted(results, key=lambda r: (r["status"] == "excluded", -r["score"], r["id"]))
