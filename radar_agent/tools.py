"""工具 = 普通 Python 函数 + 参数说明 + 校验与执行入口。"""

from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser

from .http import NetworkError, request_json

API = "https://hacker-news.firebaseio.com/v0"
FEEDS = {"new", "top", "ask", "show", "job"}


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value, limit=3000):
    parser = TextParser()
    parser.feed(str(value or ""))
    return " ".join(" ".join(parser.parts).split())[:limit]


def integer(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} 必须是 {minimum}～{maximum} 的整数。")


def schema(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object", "properties": properties,
                "required": required, "additionalProperties": False,
            },
        },
    }


TOOL_SCHEMAS = [
    schema("get_posts", "获取 Hacker News 候选帖子。仅包含站内文本，不读取外链正文。"
           "可换 feed 或 offset 获取另一批；不是全网关键词搜索。", {
        "feed": {"type": "string", "enum": sorted(FEEDS)},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        "offset": {"type": "integer", "minimum": 0, "maximum": 499},
    }, ["feed", "limit", "offset"]),
    schema("get_post", "获取一个已知 HN 帖子的详情与站内正文，外部文章未抓取。", {
        "post_id": {"type": "integer", "minimum": 1},
    }, ["post_id"]),
    schema("get_comments", "获取一个帖子的评论样本，包含部分回复，并非全部评论。"
           "用于补充需求、争议和使用反馈的原始证据。", {
        "post_id": {"type": "integer", "minimum": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": 15},
    }, ["post_id", "limit"]),
]


class HackerNewsTools:
    def __init__(self, fetch=request_json):
        self.fetch = fetch
        self.cache = {}

    def _item(self, item_id):
        integer(item_id, "post_id", 1, 10**12)
        if item_id not in self.cache:
            value = self.fetch(f"{API}/item/{item_id}.json")
            if value is not None and not isinstance(value, dict):
                raise ValueError("帖子接口返回格式不正确。")
            self.cache[item_id] = value
        return self.cache[item_id]

    def get_post(self, post_id):
        item = self._item(post_id)
        if not item or item.get("deleted") or item.get("dead"):
            return {"found": False, "post_id": post_id}
        if item.get("type") not in {"story", "job", "poll"}:
            raise ValueError("该 ID 不是帖子，请使用帖子 ID。")
        discussion = f"https://news.ycombinator.com/item?id={post_id}"
        timestamp = item.get("time")
        published = datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp else None
        return {
            "found": True, "id": post_id, "title": plain_text(item.get("title")),
            "type": item.get("type"), "text": plain_text(item.get("text")),
            "url": item.get("url") or discussion, "discussion_url": discussion,
            "published_at": published, "score": item.get("score", 0),
            "comment_count": item.get("descendants", 0), "source": "Hacker News",
            "external_article_fetched": False,
        }

    def get_posts(self, feed="new", limit=10, offset=0):
        if not isinstance(feed, str) or feed not in FEEDS:
            raise ValueError("feed 必须是 new/top/ask/show/job。")
        integer(limit, "limit", 1, 20)
        integer(offset, "offset", 0, 499)
        # 同一次运行固定列表快照，使 offset 翻页和去重可重复。
        key = f"feed:{feed}"
        if key not in self.cache:
            self.cache[key] = self.fetch(f"{API}/{feed}stories.json")
        ids = self.cache[key]
        if not isinstance(ids, list):
            raise ValueError("列表接口返回格式不正确。")
        posts, errors, seen = [], [], set()
        for post_id in ids[offset:offset + limit]:
            try:
                integer(post_id, "post_id", 1, 10**12)
                if post_id in seen:
                    continue
                seen.add(post_id)
                post = self.get_post(post_id)
                if post["found"]:
                    posts.append(post)
            except (NetworkError, ValueError, OverflowError) as error:
                errors.append({"post_id": post_id, "error": str(error)})
        next_offset = offset + limit if offset + limit < len(ids) else None
        return {"feed": feed, "offset": offset, "posts": posts, "errors": errors,
                "next_offset": next_offset, "coverage": "当前列表中的一批候选，不是全站搜索"}

    def get_comments(self, post_id, limit=5):
        integer(limit, "limit", 1, 15)
        post = self.get_post(post_id)
        if not post["found"]:
            return {"post_id": post_id, "comments": [], "error": "帖子不存在或已删除"}
        queue = deque((child, 0) for child in self._item(post_id).get("kids", []))
        comments, errors, seen = [], [], set()
        inspected = 0
        while queue and len(comments) < limit and inspected < 30:
            comment_id, depth = queue.popleft()
            if comment_id in seen:
                continue
            seen.add(comment_id)
            inspected += 1
            try:
                item = self._item(comment_id)
                if not item:
                    continue
                queue.extend((child, depth + 1) for child in item.get("kids", []))
                if item.get("deleted") or item.get("dead") or item.get("type") != "comment":
                    continue
                comments.append({
                    "id": comment_id, "parent": item.get("parent"), "depth": depth,
                    "text": plain_text(item.get("text")),
                    "url": f"https://news.ycombinator.com/item?id={comment_id}",
                })
            except (NetworkError, ValueError) as error:
                errors.append({"comment_id": comment_id, "error": str(error)})
        return {"post_id": post_id, "comments": comments, "errors": errors,
                "sample_only": True, "truncated": bool(queue), "inspected": inspected}

    def execute(self, name, arguments):
        """只允许显式注册的工具；模型不能执行任意 Python 或网址。"""
        try:
            if not isinstance(arguments, dict):
                raise ValueError("工具参数必须是 JSON 对象。")
            definition = next((x["function"] for x in TOOL_SCHEMAS
                               if x["function"]["name"] == name), None)
            if definition is None:
                raise ValueError(f"未注册的工具：{name}")
            parameters = definition["parameters"]
            if set(arguments) - set(parameters["properties"]):
                raise ValueError("工具参数包含未知字段。")
            if set(parameters["required"]) - set(arguments):
                raise ValueError("缺少必填工具参数。")
            handlers = {"get_posts": self.get_posts, "get_post": self.get_post,
                        "get_comments": self.get_comments}
            return {"ok": True, "data": handlers[name](**arguments)}
        except (NetworkError, ValueError, TypeError, OverflowError) as error:
            return {"ok": False, "error": str(error)}
