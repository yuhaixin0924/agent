posts = [
    {
        "title": "从零搭建一个 Agent",
        "category": "学习",
        "url": "https://example.com/agent"
    },
    {
        "title": "开发者需要更方便的日志分析工具",
        "category": "需求",
        "url": "https://example.com/logs"
    },
    {
        "title": "计算机实习、开源活动、竞赛和项目合作，重点关注 Agent、后端和自动化",
        "category": "机会",
        "url": "https://example.com/logs"
    }
]

for post in posts:
    if post["category"]=="学习":
        print(post["title"])
        print(post["url"])
        print(post["category"])
