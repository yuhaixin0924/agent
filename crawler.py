import json
from pathlib import Path
from urllib.request import urlopen


def fetch_json(url):
    """请求一个 URL，将返回的 JSON 转成 Python 对象。"""
    with urlopen(url, timeout=15) as response:
        text = response.read().decode("utf-8")

    return json.loads(text)


def fetch_post(post_id):
    """获取一条帖子，并整理成统一格式。"""
    api_url = (
        f"https://hacker-news.firebaseio.com/v0/item/{post_id}.json"
    )
    item = fetch_json(api_url)

    # 帖子可能不存在，或已被删除。
    if not item or item.get("deleted") or item.get("dead"):
        return None

    discussion_url = f"https://news.ycombinator.com/item?id={post_id}"

    return {
        "id": item["id"],
        "title": item.get("title", ""),
        "url": item.get("url") or discussion_url,
        "discussion_url": discussion_url,
        "text": item.get("text", ""),
        "published_at": item.get("time"),
        "source": "Hacker News",
        "category": "未分类"
    }


def main():
    list_url = (
        "https://hacker-news.firebaseio.com/v0/newstories.json"
    )
    post_ids = fetch_json(list_url)

    posts = []

    for post_id in post_ids[:5]:
        try:
            post = fetch_post(post_id)

            if post is not None:
                posts.append(post)
                print(f"采集成功：{post['title']}")

        except Exception as error:
            print(f"采集失败，帖子 ID={post_id}：{error}")

    # 保存在脚本所在目录，避免受终端当前目录影响。
    output_path = Path(__file__).with_name("hn_items.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(posts, file, ensure_ascii=False, indent=2)

    print(f"\n保存了 {len(posts)} 条记录：{output_path}")
    

if __name__ == "__main__":
    main()
