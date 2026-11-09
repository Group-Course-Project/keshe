# -*- coding: utf-8 -*-
import statistics
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import EnrollmentRecord, School, SchoolTalent

CHONGLIU = {"碑林区", "新城区", "莲湖区", "雁塔区", "未央区", "灞桥区"}
TIER_RULES = [
    ("冲", 0.85, 1.00),
    ("稳", 1.00, 1.20),
    ("保", 1.20, float("inf")),
]
STATUS_QUALITY = {
    "正常": 1.0,
    "约": 0.9,
    "边界>": 0.75,
    "边界<": 0.75,
    "区间": 0.75,
}


def _usable_records(db: Session, school_id: int) -> list[EnrollmentRecord]:
    rows = db.scalars(
        select(EnrollmentRecord).where(EnrollmentRecord.school_id == school_id)
    ).all()
    return [r for r in rows if r.min_rank is not None and r.rank_status not in ("补录", "无数据", "缺失", "异常")]


def _rank_stats(db: Session, school_id: int):
    """用多年可用位次的中位数作参考，并返回波动区间。"""
    rows = _usable_records(db, school_id)
    if not rows:
        return None, None, None, None, 0
    ranks = sorted(r.min_rank for r in rows if r.min_rank is not None)
    if not ranks:
        return None, None, None, None, 0
    median = int(round(statistics.median(ranks)))
    latest = max(rows, key=lambda r: r.year)
    low, high = ranks[0], ranks[-1]
    return median, latest.year, low, high, high - low


def _reference_rank(db: Session, school_id: int):
    """兼容旧调用，返回 (多年中位数位次, 数据截至年份)。"""
    median, latest_year, _, _, _ = _rank_stats(db, school_id)
    return median, latest_year


def _rank_score(ratio: float) -> float:
    if ratio <= 0:
        return 0.0
    if 1.0 <= ratio < 1.2:
        return 100.0
    if ratio < 1.0:
        return max(0.0, 100.0 - 100.0 * (1.0 - ratio) / 0.15)
    # ratio >= 1.2：位次越“稳”，分温和衰减。
    # 用开方曲线而不是线性压到 0，这样位次很好的考生（如 300 名）
    # 也能在保底档里明显区分出顶尖学校，而不是所有学校同分甚至被清空。
    return 100.0 * (1.2 / ratio) ** 0.5


def classify(ratio: float) -> str | None:
    for tier, lo, hi in TIER_RULES:
        if lo <= ratio < hi:
            return tier
    return None


def recommend(db: Session, predicted_rank: int, target_districts: list[str],
              require_dormitory: bool, school_type_preference: str, top_k: int):
    schools = db.scalars(select(School)).all()
    candidates = []
    for s in schools:
        # v0.5：知识库补录的学校只有招生计划/录取线，没有历年位次。
        # 显式跳过，与原先 _rank_stats 返回 None 时 continue 的结果完全一致，
        # 但省掉每所新增学校的位次/特长查询，也避免误把空数据当「保底」。
        if (s.data_completeness or "full") != "full":
            continue
        # 硬性过滤
        if target_districts and s.district not in target_districts:
            continue
        if require_dormitory and not s.has_dormitory:
            continue
        if school_type_preference in ("公办", "民办") and s.school_type != school_type_preference:
            continue

        talents = db.scalars(
            select(SchoolTalent).where(SchoolTalent.school_id == s.id)
        ).all()
        talent_list = [{"category": t.category, "item": t.item} for t in talents]

        ref_rank, ref_year, rank_low, rank_high, rank_spread = _rank_stats(db, s.id)
        if ref_rank is None:
            continue
        ratio = ref_rank / predicted_rank
        tier = classify(ratio)
        if tier is None:
            continue

        usable = _usable_records(db, s.id)
        years_available = len(usable)
        if years_available >= 2 and rank_spread is not None:
            volatility = rank_spread / max(ref_rank, 1)
            stability = max(0.0, min(100.0, 100.0 - 50.0 * volatility))
        else:
            stability = min(100.0, 20.0 * years_available)
        ref_record = next((r for r in usable if r.year == ref_year), None)
        quality = STATUS_QUALITY.get(ref_record.rank_status, 0.7) if ref_record else 0.7

        rank_score = _rank_score(ratio)
        match_score = round(0.7 * rank_score + 0.2 * stability + 10.0 * quality, 1)

        reasons = [
            f"近 {years_available} 年位次中位数 {ref_rank}（截至 {ref_year} 年），考生位次比 {ratio:.2f}"
        ]
        if years_available >= 2 and rank_low is not None and rank_high is not None:
            if rank_spread / max(ref_rank, 1) > 0.35:
                reasons.append(f"位次在 {rank_low}–{rank_high} 之间来回跳，像坐过山车，大小年明显")
            else:
                reasons.append(f"位次在 {rank_low}–{rank_high} 之间，整体还算稳")
        if require_dormitory:
            reasons.append("满足住宿要求")
        if ref_record and ref_record.rank_status == "约":
            reasons.append("该年位次为估算值，别当铁律")

        candidates.append({
            "school_id": s.id,
            "name": s.name,
            "district": s.district,
            "school_type": s.school_type,
            "has_dormitory": s.has_dormitory,
            "strategy": tier,
            "match_score": match_score,
            "ref_rank": ref_rank,
            "ref_year": ref_year,
            "years_available": years_available,
            "reasons": reasons,
            "talents": talent_list,
        })

    grouped = defaultdict(list)
    for c in candidates:
        grouped[c["strategy"]].append(c)
    result = {}
    for tier in ("冲", "稳", "保"):
        items = sorted(grouped[tier], key=lambda x: (-x["match_score"], x["ref_rank"]))
        result[tier] = items[:top_k]
    return result
