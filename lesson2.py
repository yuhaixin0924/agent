import json
from urllib.request import urlopen

# 1. 请求最新帖子的 ID 列表
list_url = "https://hacker-news.firebaseio.com/v0/newstories.json"

with urlopen(list_url, timeout=15) as response:
    text = response.read().decode("utf-8")

# 2. JSON 文本转换成 Python 列表
post_ids = json.loads(text)

print("前 5 个帖子 ID：", post_ids[:5])

posts = []

for post_id in post_ids[:5]:
    detail_url = (
        f"https://hacker-news.firebaseio.com/v0/item/{post_id}.json"
    )

    with urlopen(detail_url, timeout=15) as response:
        text = response.read().decode("utf-8")

    post = json.loads(text)

    # 有些帖子可能已不存在，跳过它。
    if post is None:
        continue

    posts.append(post)

    print("标题：", post.get("title", "无标题"))
    print("链接：", post.get("url", "没有外部链接"))
    print("得分：", post.get("score", 0))
    print("评论数：", post.get("descendants", 0))
    print()

print("共采集：", len(posts), "条")
with open("hn_items.json", "w", encoding="utf-8") as file:
    json.dump(posts, file, ensure_ascii=False, indent=2)