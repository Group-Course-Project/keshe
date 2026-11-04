# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session

from ..models import School
from .recommend import _reference_rank, classify

LEVEL = {"冲": 1, "稳": 2, "保": 3}


def check_volunteers(db: Session, predicted_rank: int, school_ids: list[int]) -> dict:
    items = []
    for idx, sid in enumerate(school_ids, 1):
        school = db.get(School, sid)
        if school is None:
            continue
        ref_rank, ref_year = _reference_rank(db, sid)
        ratio = (ref_rank / predicted_rank) if ref_rank else None
        strategy = classify(ratio) if ratio else None
        items.append({
            "order": idx,
            "school_id": sid,
            "name": school.name,
            "ref_rank": ref_rank,
            "ref_year": ref_year,
            "ratio": round(ratio, 3) if ratio else None,
            "strategy": strategy,
        })

    issues = []
    for i in range(1, len(items)):
        prev, cur = items[i - 1], items[i]
        if prev["ratio"] is None or cur["ratio"] is None:
            continue
        # 位次比越大代表越容易录取，志愿顺序应“由难到易”，即 ratio 递增
        if cur["ratio"] < prev["ratio"] * 0.95:
            issues.append(
                f"第 {prev['order']}-{cur['order']} 志愿梯度倒挂："
                f"{prev['name']}（{prev['ratio']}）比 {cur['name']}（{cur['ratio']}）更容易录取，"
                "等于把保底当前锋，顺序建议调换"
            )
        prev_level = LEVEL.get(prev["strategy"] or "", None)
        cur_level = LEVEL.get(cur["strategy"] or "", None)
        if prev_level is not None and cur_level is not None and cur_level < prev_level:
            issues.append(
                f"第 {prev['order']} 志愿是{prev['strategy']}，第 {cur['order']} 志愿是{cur['strategy']}，"
                "冲稳保倒着排，等于先打硬仗；建议按“冲→稳→保”排"
            )

    counts = {"冲": 0, "稳": 0, "保": 0}
    for item in items:
        if item["strategy"] in counts:
            counts[item["strategy"]] += 1
    if items and counts["保"] == 0:
        issues.append("没有保底志愿，等于开车不系安全带；至少留 1–2 所保档，而且必须是你自己愿意读的")

    total = max(1, sum(counts.values()))
    ratio_summary = {k: round(v / total, 3) for k, v in counts.items()}
    return {"items": items, "issues": issues, "counts": counts, "ratio": ratio_summary}
