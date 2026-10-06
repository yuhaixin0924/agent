"""固定样例 + 脚本化模型替身，仅演示工具循环，不是真实模型推理。"""

import json


ITEMS = {
    1001: {"id": 1001, "type": "story", "title": "Demo: build a small agent",
           "text": "<p>示例：通过工具调用循环搭建小型 Agent。</p>", "score": 12,
           "descendants": 1, "kids": [2001]},
    1002: {"id": 1002, "type": "story", "title": "Demo: organizing saved tutorials",
           "text": "<p>示例：开发者难以找回收藏的学习资料。</p>", "score": 8},
    2001: {"id": 2001, "type": "comment", "parent": 1001,
           "text": "<p>示例反馈：希望能看到每次工具调用的参数和结果。</p>"},
}


def fixture_fetch(url):
    if "/item/" in url:
        return ITEMS.get(int(url.rsplit("/", 1)[1].split(".")[0]))
    return [1001, 1002]


class DemoClient:
    def complete(self, messages, tools, *, require_tool=False):
        observations = [m for m in messages if m["role"] == "tool"]
        if not observations:
            name, args = "get_posts", {"feed": "new", "limit": 2, "offset": 0}
        elif len(observations) == 1:
            posts = json.loads(observations[-1]["content"])["data"]["posts"]
            name, args = "get_comments", {"post_id": posts[0]["id"], "limit": 3}
        else:
            message = {"role": "assistant", "content":
                       "[离线演示：固定样例，不是真实帖子或模型判断]\n\n"
                       "学习：第一个样例演示 Agent 工具循环。\n"
                       "需求：样例评论提出查看工具参数和结果的需求，可作为待验证假设。\n"
                       "机会：样例中没有可验证的实习或竞赛信息。\n\n"
                       "循环完成：获取列表 → 读取评论 → 返回回答。"}
            return {"message": message, "usage": {}}
        message = {"role": "assistant", "content": None, "tool_calls": [{
            "id": f"demo_{len(observations)}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        }]}
        return {"message": message, "usage": {}}
