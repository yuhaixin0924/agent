"""固定岗位池评测：标签仅交给评测器，不能进入模型上下文。"""
import math
import time

from .core import ranked


def metrics(predictions, labels):
    if len(set(predictions)) != len(predictions):
        raise ValueError("预测不能包含重复岗位。")
    if any(type(v) is not int or v not in (0, 1, 2) for v in labels.values()):
        raise ValueError("标签必须是 0（不推荐）、1（值得核对）、2（优先核对）。")
    if any(p not in labels for p in predictions):
        raise ValueError("预测中存在未标注岗位，不能把未知标签当成负例。")
    gain = lambda values: sum((2 ** v - 1) / math.log2(i + 2) for i, v in enumerate(values))
    ideal = gain(sorted(labels.values(), reverse=True)[:10])
    return {"precision_at_5": sum(labels[p] > 0 for p in predictions[:5]) / 5,
            "ndcg_at_10": gain([labels[p] for p in predictions[:10]]) / ideal if ideal else 0,
            "returned": len(predictions), "positive_labels": sum(v > 0 for v in labels.values())}


def evaluate(store, cases, client=None):
    if client is not None:
        raise ValueError("当前机会评估不做岗位排名，请用人工标注检验事实、未知条件和建议；旧AI排序评测停用。")
    jobs = store.jobs()
    job_ids = {j["id"] for j in jobs}
    if not cases:
        raise ValueError("至少需要一个测试画像。")
    results = []
    for case in cases:
        if set(case["labels"]) != job_ids:
            raise ValueError("每个画像须为当前固定岗位池的所有岗位标注；不要混入开发阶段之外的新岗位。")
        started = time.monotonic()
        baseline = [r["id"] for r in ranked(jobs, case["profile"]) if r["status"] != "excluded"][:10]
        row = {"case": case["name"], "rules": metrics(baseline, case["labels"]),
               "rules_seconds": round(time.monotonic() - started, 4)}
        results.append(row)
    return {"cases": results, "note": "P@5 固定除以5，不足5条按空位处理；无正例时 NDCG=0。标签衡量推荐价值，不是录用概率。"}
