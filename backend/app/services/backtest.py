# -*- coding: utf-8 -*-
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import EnrollmentRecord

USABLE = {"正常", "约", "边界>", "边界<", "区间"}


def _classify(ratio: float, rules) -> str | None:
    for tier, lo, hi in rules:
        if lo <= ratio < hi:
            return tier
    return None


def _records_by_year(db: Session):
    rows = db.scalars(select(EnrollmentRecord)).all()
    by_year = defaultdict(dict)  # year -> school_id -> min_rank
    for r in rows:
        if r.min_rank is not None and r.rank_status in USABLE:
            by_year[r.year][r.school_id] = r.min_rank
    return by_year


def _evaluate(db: Session, rules) -> dict:
    by_year = _records_by_year(db)
    years = sorted(by_year)
    tiers = ("冲", "稳", "保")
    stats = {t: {"count": 0, "hit": 0} for t in tiers}
    per_year = defaultdict(lambda: {t: {"count": 0, "hit": 0} for t in tiers})
    sample_ranks = range(500, 30001, 250)

    for y in years[1:]:
        refs = by_year.get(y - 1, {})
        cutoffs = by_year.get(y, {})
        for sid, cutoff in cutoffs.items():
            ref = refs.get(sid)
            if ref is None:
                continue
            for r in sample_ranks:
                ratio = ref / r
                tier = _classify(ratio, rules)
                if tier is None:
                    continue
                admitted = r <= cutoff
                stats[tier]["count"] += 1
                stats[tier]["hit"] += int(admitted)
                per_year[y][tier]["count"] += 1
                per_year[y][tier]["hit"] += int(admitted)

    result = {"tiers": {}, "years": {}}
    for t in tiers:
        c, h = stats[t]["count"], stats[t]["hit"]
        result["tiers"][t] = {
            "count": c,
            "hit": h,
            "hit_rate": round(h / c, 3) if c else None,
        }
    for y in sorted(per_year):
        result["years"][str(y)] = {
            t: {
                "count": per_year[y][t]["count"],
                "hit": per_year[y][t]["hit"],
                "hit_rate": round(per_year[y][t]["hit"] / per_year[y][t]["count"], 3)
                if per_year[y][t]["count"]
                else None,
            }
            for t in tiers
        }
    return result


def _tier_score(rate, lo, hi):
    if rate is None:
        return 0.0
    if rate < lo:
        return max(0.0, 1.0 - (lo - rate) / lo)
    if rate > hi:
        return max(0.0, 1.0 - (rate - hi) / (1.0 - hi))
    return 1.0


def grid_search(db: Session):
    candidates = []
    for chong_hi in (0.90, 0.95, 1.00, 1.05):
        for wen_hi in (1.10, 1.15, 1.20, 1.25, 1.30):
            for bao_hi in (1.40, 1.50, 1.60):
                rules = [("冲", 0.80, chong_hi), ("稳", chong_hi, wen_hi), ("保", wen_hi, bao_hi)]
                res = _evaluate(db, rules)["tiers"]
                chong = res["冲"]["hit_rate"]
                wen = res["稳"]["hit_rate"]
                bao = res["保"]["hit_rate"]
                score = (
                    0.4 * _tier_score(chong, 0.20, 0.50)
                    + 0.3 * _tier_score(wen, 0.55, 0.85)
                    + 0.3 * _tier_score(bao, 0.90, 1.00)
                )
                candidates.append({
                    "rules": {"冲": [0.80, chong_hi], "稳": [chong_hi, wen_hi], "保": [wen_hi, bao_hi]},
                    "hit_rate": {"冲": chong, "稳": wen, "保": bao},
                    "score": round(score, 3),
                })
    candidates.sort(key=lambda x: -x["score"])
    return candidates[:5]


def run_backtest(db: Session):
    default_rules = [("冲", 0.85, 1.00), ("稳", 1.00, 1.20), ("保", 1.20, 1.50)]
    return {
        "default_rules": {"冲": [0.85, 1.00], "稳": [1.00, 1.20], "保": [1.20, 1.50]},
        "default": _evaluate(db, default_rules),
        "top_sets": grid_search(db),
    }
