# -*- coding: utf-8 -*-
import json
import secrets
import statistics
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .auth import (
    create_session,
    find_user_by_username,
    get_optional_user,
    hash_password,
    require_user,
    revoke_session,
    user_out,
    verify_password,
)
from .database import get_db
from .migrate import run_migrations
from .models import (
    AdmissionScore,
    AnalysisReport,
    AppUser,
    CandidateProfile,
    ControlLine,
    DataSource,
    EnrollmentPlan,
    EnrollmentRecord,
    MockVolunteer,
    RecommendationResult,
    School,
    SchoolAlias,
    SchoolProfile,
    SchoolTalent,
    ScoreRankMap,
    VolunteerPlan,
)
from .schemas import (
    Candidate,
    CompareIn,
    LoginIn,
    PlanIn,
    PlanUpdateIn,
    ProfileIn,
    RegisterIn,
    TrendPoint,
    VolunteerCheckIn,
)
from .services.backtest import run_backtest
from .services.llm import generate_report
from .services.recommend import recommend
from .services.volunteer import check_volunteers


@asynccontextmanager
async def lifespan(_app):
    # 启动时自动建新表 / 补旧列，避免 create_all 不给已存在表加列导致旧库报错
    actions = run_migrations()
    if actions:
        print("[migrate] 已执行:", ", ".join(actions))
    yield


app = FastAPI(title="西安中考志愿智能分析推荐系统", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- 公共工具
def _identity_user(identity) -> AppUser | None:
    return identity[0] if identity else None


def _canonical_map(db: Session, names: list[str]) -> dict[str, set[str]]:
    """{展示用校名: 该校在知识库里可能出现的全部写法}。

    school_alias 只有 72 行，一次读全表即可，避免逐名查询。
    没有别名的学校返回 {自身}，行为与归一前完全一致。
    """
    aliases = db.scalars(select(SchoolAlias)).all()
    by_alias = {a.alias: a.canonical_name for a in aliases}
    by_canonical: dict[str, set[str]] = defaultdict(set)
    for a in aliases:
        by_canonical[a.canonical_name].add(a.alias)
    out: dict[str, set[str]] = {}
    for name in names:
        canonical = by_alias.get(name, name)
        out[name] = {name, canonical} | by_canonical.get(canonical, set())
    return out


def _school_context(db: Session, grouped: dict, limit: int = 8) -> str:
    """把外部采集知识库里的学校公开资料拼成 AI 报告上下文。

    只取候选清单里能匹配到档案/招生计划的学校，控制条数避免 Prompt 过长。
    知识库为空时返回空串，报告行为与升级前完全一致。
    """
    names: list[str] = []
    for tier in ("冲", "稳", "保"):
        for c in grouped.get(tier, []):
            n = c.get("name")
            if n and n not in names:
                names.append(n)
    names = names[:limit]
    if not names:
        return ""
    # v0.5：知识库里同一所学校可能有多个写法，按归一映射展开后再匹配
    cmap = _canonical_map(db, names)
    all_variants = set().union(*cmap.values())
    profiles = {
        p.school_name: p
        for p in db.scalars(
            select(SchoolProfile).where(SchoolProfile.school_name.in_(all_variants))
        ).all()
    }
    plans = {
        p.school_name: p
        for p in db.scalars(
            select(EnrollmentPlan).where(EnrollmentPlan.school_name.in_(all_variants))
        ).all()
    }

    def pick(mapping: dict, variants: set[str]):
        for v in sorted(variants, key=lambda x: (x not in mapping, len(x))):
            if v in mapping:
                return mapping[v]
        return None

    lines: list[str] = []
    for name in names:
        bits: list[str] = []
        p = pick(profiles, cmap[name])
        if p:
            if p.tuition:
                bits.append("学费：" + p.tuition)
            if p.dorm_fee:
                bits.append("住宿费：" + p.dorm_fee)
            if p.boarding:
                bits.append("食宿：" + p.boarding[:60])
            if p.address:
                bits.append("地址：" + p.address)
            if p.features:
                bits.append("特色：" + p.features[:70])
        pl = pick(plans, cmap[name])
        if pl:
            if pl.plan_total:
                bits.append(f"2025招生计划约{pl.plan_total}人")
            if pl.sport_items or pl.art_items:
                bits.append("特长项目：" + "、".join(
                    x for x in [pl.sport_items, pl.art_items] if x)[:60])
        if bits:
            lines.append(f"- {name}：" + "；".join(bits))
    return "\n".join(lines)


def _create_profile(
    db: Session,
    predicted_rank: int,
    target_districts: list[str],
    require_dormitory: bool,
    school_type_preference: str,
    user_id: int | None = None,
) -> int:
    profile = CandidateProfile(
        predicted_rank=predicted_rank,
        target_districts=",".join(target_districts),
        require_dormitory=require_dormitory,
        school_type_preference=school_type_preference,
        user_id=user_id,
    )
    db.add(profile)
    db.flush()
    return profile.id


def _usable_profile_id(db: Session, profile_id: int | None, user: AppUser | None) -> int | None:
    """只允许复用匿名画像或本人画像，避免跨账号串数据。"""
    if profile_id is None:
        return None
    profile = db.get(CandidateProfile, profile_id)
    if profile is None:
        return None
    if profile.user_id is not None and (user is None or profile.user_id != user.id):
        return None
    return profile.id


def _save_recommendations(db: Session, profile_id: int, grouped: dict) -> None:
    for tier, items in grouped.items():
        for c in items:
            db.add(
                RecommendationResult(
                    profile_id=profile_id,
                    school_id=c["school_id"],
                    strategy=tier,
                    match_score=c["match_score"],
                    reasons_json=json.dumps(c["reasons"], ensure_ascii=False),
                )
            )


def _iso(value) -> str:
    return value.isoformat(sep=" ", timespec="seconds") if value else ""


def _plan_out(plan: VolunteerPlan) -> dict:
    return {
        "id": plan.id,
        "name": plan.name,
        "profile": json.loads(plan.profile_json or "{}"),
        "volunteers": json.loads(plan.volunteers_json or "[]"),
        "summary": json.loads(plan.summary_json or "{}"),
        "share_token": plan.share_token,
        "created_at": _iso(plan.created_at),
        "updated_at": _iso(plan.updated_at),
    }


def _owned_plan(db: Session, plan_id: int, user: AppUser) -> VolunteerPlan:
    plan = db.get(VolunteerPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="方案不存在")
    if plan.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该方案")
    return plan


# ---------------------------------------------------------------- 健康检查
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------- 账号体系
@app.post("/auth/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if find_user_by_username(db, username) is not None:
        raise HTTPException(status_code=400, detail="该用户名已被注册")
    user = AppUser(
        username=username,
        display_name=(payload.display_name.strip() or username),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token, _ = create_session(db, user.id)
    return {"token": token, "user": user_out(user)}


@app.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = find_user_by_username(db, payload.username.strip())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    token, _ = create_session(db, user.id)
    return {"token": token, "user": user_out(user)}


@app.get("/auth/me")
def me(identity=Depends(get_optional_user)):
    user = _identity_user(identity)
    return {"user": user_out(user) if user else None}


@app.post("/auth/logout")
def logout(identity=Depends(get_optional_user), db: Session = Depends(get_db)):
    token = identity[1] if identity else None
    if token:
        revoke_session(db, token)
    return {"ok": True}


# ---------------------------------------------------------------- 学校 / 特长生数据
@app.get("/talents/items")
def talent_items(db: Session = Depends(get_db)):
    rows = db.scalars(select(SchoolTalent)).all()
    sports = sorted({r.item for r in rows if r.category == "体育"})
    arts = sorted({r.item for r in rows if r.category == "艺术"})
    return {"体育": sports, "艺术": arts}


@app.get("/talents/schools")
def talent_schools(category: str = "体育", items: str = "", db: Session = Depends(get_db)):
    item_list = [x.strip() for x in items.split(",") if x.strip()]
    q = (
        select(School)
        .join(SchoolTalent, SchoolTalent.school_id == School.id)
        .where(SchoolTalent.category == category)
    )
    if item_list:
        q = q.where(SchoolTalent.item.in_(item_list))
    schools = db.scalars(q.distinct()).all()
    result = []
    for s in schools:
        talents = db.scalars(
            select(SchoolTalent).where(SchoolTalent.school_id == s.id)
        ).all()
        result.append({
            "id": s.id,
            "name": s.name,
            "district": s.district,
            "school_type": s.school_type,
            "has_dormitory": s.has_dormitory,
            "talents": [{"category": t.category, "item": t.item} for t in talents],
        })
    return {
        "notice": "体育、艺术特长生按“专项测试 + 文化课过线”录取；2025 年城六区体育、艺术特长生录取控制线为 366.6 分，与文化课统招控制线 611.0 分不同，位次数据仅供参考，不可直接类比。",
        "schools": result,
    }


@app.get("/schools")
def list_schools(db: Session = Depends(get_db)):
    rows = db.scalars(select(School).order_by(School.id)).all()
    out = []
    for s in rows:
        talents = db.scalars(
            select(SchoolTalent).where(SchoolTalent.school_id == s.id)
        ).all()
        out.append({
            "id": s.id,
            "name": s.name,
            "district": s.district,
            "school_type": s.school_type,
            "has_dormitory": s.has_dormitory,
            "note": s.note,
            "data_completeness": s.data_completeness or "full",
            "source_summary": s.source_summary or "",
            "has_rank_data": (s.data_completeness or "full") == "full",
            "talents": [{"category": t.category, "item": t.item} for t in talents],
        })
    return out


@app.post("/schools/compare")
def compare_schools(payload: CompareIn, db: Session = Depends(get_db)):
    """一次返回多所学校的画像 + 历年位次 + 统计，供对比页使用。"""
    result = []
    for school_id in dict.fromkeys(payload.school_ids):  # 去重且保持用户选择顺序
        school = db.get(School, school_id)
        if school is None:
            continue
        records = db.scalars(
            select(EnrollmentRecord)
            .where(EnrollmentRecord.school_id == school.id)
            .order_by(EnrollmentRecord.year)
        ).all()
        ranks = [r.min_rank for r in records if r.min_rank is not None]
        trends = [
            {"year": r.year, "min_rank": r.min_rank, "status": r.rank_status}
            for r in records
        ]
        latest = records[-1] if records else None
        talents = db.scalars(
            select(SchoolTalent).where(SchoolTalent.school_id == school.id)
        ).all()
        result.append({
            "id": school.id,
            "name": school.name,
            "district": school.district,
            "school_type": school.school_type,
            "has_dormitory": school.has_dormitory,
            "note": school.note,
            "data_completeness": school.data_completeness or "full",
            "source_summary": school.source_summary or "",
            "has_rank_data": bool(ranks),
            "talents": [{"category": t.category, "item": t.item} for t in talents],
            "trend": trends,
            "stats": {
                "latest_year": latest.year if latest else None,
                "latest_rank": latest.min_rank if latest else None,
                "median_rank": round(statistics.median(ranks), 1) if ranks else None,
                "best_rank": min(ranks) if ranks else None,
                "worst_rank": max(ranks) if ranks else None,
                "years_available": len(ranks),
                "estimated_years": sum(
                    1 for r in records if r.min_rank is not None and r.rank_status != "正常"
                ),
            },
        })
    no_rank = sum(1 for s in result if not s["has_rank_data"])
    notice = "位次越小越靠前；标注“约/补录/区间”的记录为估算值，对比时请留意数据口径。"
    if no_rank:
        notice += (
            f" 本次有 {no_rank} 所学校暂无历年位次记录，位次指标显示为空，"
            "仅可用招生计划/录取线等资料，不参与冲稳保推荐。"
        )
    return {"schools": result, "notice": notice}


@app.get("/schools/{school_id}/trend", response_model=list[TrendPoint])
def school_trend(school_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(EnrollmentRecord)
        .where(EnrollmentRecord.school_id == school_id)
        .order_by(EnrollmentRecord.year)
    ).all()
    return [
        TrendPoint(year=r.year, min_rank=r.min_rank, status=r.rank_status)
        for r in rows
    ]


# ---------------------------------------------------------------- 学校档案（v0.6）
# 分区渐进式详情：六个数据区块各自判空并给出缺失原因，前端只渲染有数据的区块。
# 原则：不臆造数据。非 full 学校的 has_dormitory=False 表示「未采集」，不是「不提供」。
PROFILE_FIELDS = [
    ("address", "学校地址"),
    ("admission_code", "招生代码"),
    ("official_site", "官方网站"),
    ("phone", "联系电话"),
    ("tuition", "学费"),
    ("dorm_fee", "住宿费"),
    ("boarding", "食宿条件"),
    ("plan_2025", "2025 招生计划说明"),
    ("talent_info", "特长生信息"),
    ("features", "办学特色"),
]

MISSING_REASON = {
    "rank": "官方未逐校公布城六区录取位次，本校暂无历年位次记录，因此不参与冲稳保推荐。",
    "admission_lines": "知识库未采集到该校的逐校录取线。",
    "enrollment_plan": "2025 年官方招生计划中未匹配到该校。",
    "talents": "暂无该校特长生项目记录（不等于该校不招收特长生）。",
    "profile": "尚未采集该校招生简章，暂无地址、收费、食宿等校园档案。",
}


@app.get("/schools/{school_id}/detail")
def school_detail(school_id: int, db: Session = Depends(get_db)):
    """聚合一所学校的全部已有资料：位次 / 录取线 / 招生计划 / 特长生 / 校园档案 / 来源。"""
    school = db.get(School, school_id)
    if school is None:
        raise HTTPException(status_code=404, detail="学校不存在")

    is_full = (school.data_completeness or "full") == "full"
    # 同一所学校在外部资料里可能有多种写法，按人工归一表展开后再匹配
    variants = _canonical_map(db, [school.name])[school.name]
    name_match = or_(
        AdmissionScore.school_name.in_(variants),
        AdmissionScore.raw_name.in_(variants),
    )
    plan_match = or_(
        EnrollmentPlan.school_name.in_(variants),
        EnrollmentPlan.raw_name.in_(variants),
    )
    profile_match = or_(
        SchoolProfile.school_name.in_(variants),
        SchoolProfile.raw_name.in_(variants),
    )

    records = db.scalars(
        select(EnrollmentRecord)
        .where(EnrollmentRecord.school_id == school_id)
        .order_by(EnrollmentRecord.year)
    ).all()
    usable = [
        r for r in records
        if r.min_rank is not None
        and r.rank_status not in ("补录", "无数据", "缺失", "异常")
    ]
    ranks = [r.min_rank for r in usable]
    rank_items = [{
        "year": r.year, "min_rank": r.min_rank,
        "status": r.rank_status, "raw_value": r.raw_value,
    } for r in records]
    sections: dict = {
        "rank": {
            "available": bool(ranks),
            "reason": "" if ranks else MISSING_REASON["rank"],
            "items": rank_items,
            "stats": {
                "latest_year": usable[-1].year if usable else None,
                "latest_rank": usable[-1].min_rank if usable else None,
                "median_rank": round(statistics.median(ranks), 1) if ranks else None,
                "best_rank": min(ranks) if ranks else None,
                "worst_rank": max(ranks) if ranks else None,
                "years_available": len(ranks),
                "estimated_years": sum(1 for r in usable if r.rank_status != "正常"),
            },
        },
    }

    # 录取线按满分制分组展示：700 / 820 分制不可混着比较
    lines = db.scalars(
        select(AdmissionScore).where(name_match)
        .order_by(AdmissionScore.year, AdmissionScore.id)
    ).all()
    by_scale: dict[int, list[dict]] = defaultdict(list)
    for r in lines:
        by_scale[r.full_score].append({
            "year": r.year, "full_score": r.full_score,
            "unified_line": r.unified_line, "transfer_line": r.transfer_line,
            "score_rate": r.score_rate, "school_level": r.school_level,
            "school_nature": r.school_nature, "batch": r.batch,
            "match_status": r.match_status, "source_id": r.source_id,
            "credibility": r.credibility, "note": r.note,
        })
    sections["admission_lines"] = {
        "available": bool(lines),
        "reason": "" if lines else MISSING_REASON["admission_lines"],
        "scales": [{
            "full_score": score,
            "years": f"{rows[0]['year']}–{rows[-1]['year']}",
            "items": rows,
        } for score, rows in sorted(by_scale.items())],
        "total": len(lines),
        "notice": "逐校录取线为第三方汇总（非官方发布）；不同满分制的分数不可直接比较，跨年比较请在同一分制内看得分率。",
    }

    plans = db.scalars(
        select(EnrollmentPlan).where(plan_match)
        .order_by(EnrollmentPlan.year.desc(), EnrollmentPlan.id)
    ).all()
    sections["enrollment_plan"] = {
        "available": bool(plans),
        "reason": "" if plans else MISSING_REASON["enrollment_plan"],
        "items": [{
            "year": p.year, "school_nature": p.school_nature,
            "plan_total": p.plan_total, "unified_plan": p.unified_plan,
            "directed_plan": p.directed_plan,
            "sport_talent_plan": p.sport_talent_plan,
            "art_talent_plan": p.art_talent_plan,
            "feature_classes": p.feature_classes,
            "sport_items": p.sport_items, "art_items": p.art_items,
            "single_plan": p.single_plan,
            "source_id": p.source_id, "credibility": p.credibility,
            "note": p.note,
        } for p in plans],
    }

    talents = db.scalars(
        select(SchoolTalent).where(SchoolTalent.school_id == school_id)
        .order_by(SchoolTalent.category, SchoolTalent.item)
    ).all()
    sections["talents"] = {
        "available": bool(talents),
        "reason": "" if talents else MISSING_REASON["talents"],
        "items": [{"category": t.category, "item": t.item} for t in talents],
    }

    profiles = db.scalars(
        select(SchoolProfile).where(profile_match).order_by(SchoolProfile.id)
    ).all()

    def first_value(attr: str) -> str:
        for p in profiles:
            value = (getattr(p, attr) or "").strip()
            if value:
                return value
        return ""

    fields = [
        {"label": label, "value": first_value(attr)}
        for attr, label in PROFILE_FIELDS
        if first_value(attr)
    ]
    sections["profile"] = {
        "available": bool(fields),
        "reason": "" if fields else MISSING_REASON["profile"],
        "fields": fields,
        "source_url": first_value("source_url"),
        "credibility": first_value("credibility"),
        "notice": (
            f"校园档案共 {len(PROFILE_FIELDS)} 个字段，本校采集到 {len(fields)} 个；"
            "未列出的字段表示尚未采集，不代表学校不提供。"
        ) if fields else "",
    }

    source_ids = {
        r.source_id for r in list(lines) + list(plans) if r.source_id
    }
    sources = [{
        "id": s.id, "name": s.name, "url": s.url, "kind": s.kind,
        "credibility": s.credibility, "note": s.note,
    } for s in db.scalars(
        select(DataSource).where(DataSource.id.in_(source_ids)).order_by(DataSource.id)
    ).all()] if source_ids else []
    if ranks:
        sources.append({
            "id": "LOCAL", "name": "本地历年位次数据集", "url": "",
            "kind": "项目内置数据", "credibility": "—",
            "note": "由 import_data.py 导入，含估算/边界标记，详见位次区块的 status 列。",
        })

    aliases = db.scalars(
        select(SchoolAlias).where(SchoolAlias.school_id == school_id)
        .order_by(SchoolAlias.id)
    ).all()
    missing = [v["reason"] for v in sections.values() if not v["available"]]
    return {
        "school": {
            "id": school.id,
            "name": school.name,
            "district": school.district or "待核实",
            "school_type": school.school_type or "待核实",
            "dormitory_text": ("提供" if school.has_dormitory else "不提供")
                              if is_full else "未采集",
            "dormitory_note": (
                "示例数据集中的住宿字段为随机生成的占位值，尚未与官方公示核对，不可作为择校依据。"
                if is_full else
                "该校住宿信息未采集；「未采集」不等于「不提供」。"
            ),
            "data_completeness": school.data_completeness or "full",
            "has_rank_data": is_full,
            "source_summary": school.source_summary or "",
            "note": school.note or "",
            "aliases": [a.alias for a in aliases],
        },
        "sections": sections,
        "sources": sources,
        "coverage": {
            "total": len(sections),
            "available": sum(1 for v in sections.values() if v["available"]),
            "missing": missing,
        },
        "disclaimer": "资料仅供择校参考：逐校录取线为第三方汇总（非官方发布），"
                      "2020–2024 为 700 分制、2025 为 820 分制，收费与计划以学校/教育部门当年公示为准。",
    }


# ---------------------------------------------------------------- 推荐 / 报告 / 志愿
@app.post("/recommend")
def create_recommendation(
    profile: ProfileIn,
    identity=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    user = _identity_user(identity)
    grouped = recommend(
        db,
        predicted_rank=profile.predicted_rank,
        target_districts=profile.target_districts,
        require_dormitory=profile.require_dormitory,
        school_type_preference=profile.school_type_preference,
        top_k=profile.top_k,
    )
    profile_id = _create_profile(
        db,
        profile.predicted_rank,
        profile.target_districts,
        profile.require_dormitory,
        profile.school_type_preference,
        user_id=user.id if user else None,
    )
    _save_recommendations(db, profile_id, grouped)
    db.commit()
    result = {
        tier: [Candidate(**c).model_dump() for c in items]
        for tier, items in grouped.items()
    }
    result["profile_id"] = profile_id
    return result


@app.post("/report")
def create_report(
    profile: ProfileIn,
    identity=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    user = _identity_user(identity)
    grouped = recommend(
        db,
        predicted_rank=profile.predicted_rank,
        target_districts=profile.target_districts,
        require_dormitory=profile.require_dormitory,
        school_type_preference=profile.school_type_preference,
        top_k=profile.top_k,
    )
    profile_id = _usable_profile_id(db, profile.profile_id, user)
    if profile_id is None:
        profile_id = _create_profile(
            db,
            profile.predicted_rank,
            profile.target_districts,
            profile.require_dormitory,
            profile.school_type_preference,
            user_id=user.id if user else None,
        )
    # /recommend 已保存候选结果，这里不再重复写入 recommendation_result，避免同一画像产生重复记录
    preferences = {
        "school_type_preference": profile.school_type_preference,
        "require_dormitory": profile.require_dormitory,
        "target_districts": profile.target_districts,
    }
    content, model, used_fallback = generate_report(
        profile.predicted_rank, grouped, preferences,
        school_context=_school_context(db, grouped),
    )
    report = AnalysisReport(
        profile_id=profile_id,
        model=model,
        prompt_version="v1",
        content=content,
        user_id=user.id if user else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {
        "profile_id": profile_id,
        "report_id": report.id,
        "content": content,
        "model": model,
        "fallback": used_fallback,
    }


@app.post("/volunteer/check")
def check_volunteer_order(
    payload: VolunteerCheckIn,
    identity=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    user = _identity_user(identity)
    result = check_volunteers(db, payload.predicted_rank, payload.school_ids)
    profile_id = _usable_profile_id(db, payload.profile_id, user)
    if profile_id is None:
        profile_id = _create_profile(
            db, payload.predicted_rank, [], False, "不限",
            user_id=user.id if user else None,
        )
    db.query(MockVolunteer).filter(MockVolunteer.profile_id == profile_id).delete()
    for item in result["items"]:
        db.add(
            MockVolunteer(
                profile_id=profile_id,
                order_no=item["order"],
                school_id=item["school_id"],
                strategy=item["strategy"] or "",
                gradient_check_json=json.dumps(result["issues"], ensure_ascii=False),
            )
        )
    db.commit()
    result["profile_id"] = profile_id
    return result


@app.get("/reports")
def list_reports(identity=Depends(get_optional_user), db: Session = Depends(get_db)):
    user = _identity_user(identity)
    query = (
        select(AnalysisReport, CandidateProfile)
        .join(CandidateProfile, AnalysisReport.profile_id == CandidateProfile.id)
        .order_by(AnalysisReport.created_at.desc())
        .limit(100)
    )
    # 登录用户只看本人报告；未登录只看历史匿名报告
    if user:
        query = query.where(AnalysisReport.user_id == user.id)
    else:
        query = query.where(AnalysisReport.user_id.is_(None))
    rows = db.execute(query).all()
    return [
        {
            "id": r.id,
            "profile_id": p.id,
            "predicted_rank": p.predicted_rank,
            "model": r.model,
            "created_at": _iso(r.created_at),
            "preview": (r.content or "")[:120],
        }
        for r, p in rows
    ]


@app.get("/reports/{report_id}")
def get_report(
    report_id: int,
    identity=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    user = _identity_user(identity)
    report = db.get(AnalysisReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    if user:
        if report.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权查看该报告")
    elif report.user_id is not None:
        raise HTTPException(status_code=403, detail="该报告属于已登录用户，请先登录")
    profile = db.get(CandidateProfile, report.profile_id)
    return {
        "id": report.id,
        "profile_id": report.profile_id,
        "predicted_rank": profile.predicted_rank if profile else None,
        "model": report.model,
        "prompt_version": report.prompt_version,
        "content": report.content,
        "created_at": _iso(report.created_at),
    }


# ---------------------------------------------------------------- 多套志愿方案
@app.get("/plans")
def list_plans(user: AppUser = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(VolunteerPlan)
        .where(VolunteerPlan.user_id == user.id)
        .order_by(VolunteerPlan.updated_at.desc())
    ).all()
    return [_plan_out(p) for p in rows]


@app.post("/plans")
def create_plan(
    payload: PlanIn,
    user: AppUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    plan = VolunteerPlan(
        user_id=user.id,
        name=payload.name.strip(),
        profile_json=json.dumps(payload.profile, ensure_ascii=False),
        volunteers_json=json.dumps(payload.volunteers, ensure_ascii=False),
        summary_json=json.dumps(payload.summary, ensure_ascii=False),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_out(plan)


@app.get("/plans/{plan_id}")
def get_plan(
    plan_id: int,
    user: AppUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    return _plan_out(_owned_plan(db, plan_id, user))


@app.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    payload: PlanUpdateIn,
    user: AppUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    plan = _owned_plan(db, plan_id, user)
    data = payload.model_dump(exclude_unset=True)
    field_map = {
        "profile": "profile_json",
        "volunteers": "volunteers_json",
        "summary": "summary_json",
    }
    for key, value in data.items():
        if key == "name":
            plan.name = value.strip()
        elif key in field_map:
            setattr(plan, field_map[key], json.dumps(value, ensure_ascii=False))
    plan.updated_at = datetime.now()
    db.commit()
    db.refresh(plan)
    return _plan_out(plan)


@app.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    user: AppUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    plan = _owned_plan(db, plan_id, user)
    db.delete(plan)
    db.commit()
    return {"ok": True}


@app.post("/plans/{plan_id}/share")
def enable_share(
    plan_id: int,
    user: AppUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    plan = _owned_plan(db, plan_id, user)
    if not plan.share_token:
        plan.share_token = secrets.token_urlsafe(12)
        db.commit()
        db.refresh(plan)
    return {"share_token": plan.share_token, "share_path": f"/share/{plan.share_token}"}


@app.delete("/plans/{plan_id}/share")
def disable_share(
    plan_id: int,
    user: AppUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    plan = _owned_plan(db, plan_id, user)
    plan.share_token = None
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- 公开分享（无需登录）
@app.get("/share/{token}")
def read_share(token: str, db: Session = Depends(get_db)):
    plan = db.scalar(select(VolunteerPlan).where(VolunteerPlan.share_token == token))
    if plan is None:
        raise HTTPException(status_code=404, detail="分享链接已失效或不存在")
    owner = db.get(AppUser, plan.user_id)
    return {
        "name": plan.name,
        "owner": owner.display_name if owner else "匿名用户",
        "profile": json.loads(plan.profile_json or "{}"),
        "volunteers": json.loads(plan.volunteers_json or "[]"),
        "summary": json.loads(plan.summary_json or "{}"),
        "created_at": _iso(plan.created_at),
        "disclaimer": "本方案由用户自行保存，数据仅供参考，正式志愿填报请以教育部门官方发布为准。",
    }


@app.get("/backtest")
def backtest(db: Session = Depends(get_db)):
    return run_backtest(db)


# ---------------------------------------------------------------- 外部采集知识库（只读）
# 数据由 scripts/build_knowledge_dataset.py 生成、app.import_knowledge 导入。
# 全部标注来源与可信等级；不参与冲稳保算法，仅用于查询、展示与 AI 报告上下文。
@app.get("/knowledge/summary")
def knowledge_summary(db: Session = Depends(get_db)):
    return {
        "control_lines": db.query(ControlLine).count(),
        "admission_scores": db.query(AdmissionScore).count(),
        "score_rank_rows": db.query(ScoreRankMap).count(),
        "enrollment_plans": db.query(EnrollmentPlan).count(),
        "school_profiles": db.query(SchoolProfile).count(),
        "data_sources": db.query(DataSource).count(),
        "disclaimer": "逐校录取线为第三方汇总数据（非官方发布），仅供择校参考；"
                      "2025 年中考总分由 700 改为 820，跨年分数不可直接比较。",
    }


@app.get("/knowledge/control-lines")
def knowledge_control_lines(db: Session = Depends(get_db)):
    rows = db.scalars(select(ControlLine).order_by(ControlLine.year)).all()
    return [{
        "year": r.year, "unit": r.unit, "full_score": r.full_score,
        "general_line": r.general_line, "talent_line": r.talent_line,
        "integrated_line": r.integrated_line,
        "source_id": r.source_id, "credibility": r.credibility, "note": r.note,
    } for r in rows]


@app.get("/knowledge/admission-lines")
def knowledge_admission_lines(
    school: str | None = None,
    year: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = select(AdmissionScore)
    if school:
        q = q.where(AdmissionScore.school_name.contains(school))
    if year:
        q = q.where(AdmissionScore.year == year)
    rows = db.scalars(q.order_by(AdmissionScore.school_name, AdmissionScore.year)
                      .limit(min(limit, 1000))).all()
    return [{
        "school_name": r.school_name, "year": r.year, "full_score": r.full_score,
        "unified_line": r.unified_line, "transfer_line": r.transfer_line,
        "score_rate": r.score_rate, "school_level": r.school_level,
        "school_nature": r.school_nature, "batch": r.batch,
        "source_id": r.source_id, "credibility": r.credibility,
        "match_status": r.match_status, "note": r.note,
    } for r in rows]


@app.get("/knowledge/score-to-rank")
def knowledge_score_to_rank(score: int, db: Session = Depends(get_db)):
    """2025 城六区分数 → 累计位次；无精确档时取最接近的下一档并标注。"""
    row = db.scalar(
        select(ScoreRankMap).where(ScoreRankMap.score == score)
        .order_by(ScoreRankMap.id).limit(1)
    )
    exact = True
    if row is None:
        row = db.scalar(
            select(ScoreRankMap).where(ScoreRankMap.score <= score)
            .order_by(ScoreRankMap.score.desc()).limit(1)
        )
        exact = False
    if row is None:
        raise HTTPException(status_code=404, detail="该分数低于一分一段表覆盖范围")
    return {
        "score": score, "matched_score": row.score, "exact": exact,
        "cumulative_rank": row.cumulative_rank, "ratio": row.ratio,
        "year": row.year, "full_score": row.full_score, "unit": row.unit,
        "source_id": row.source_id, "credibility": row.credibility,
        "note": "屏蔽段（特高分数段）无累计位次" if row.cumulative_rank is None
                else ("按低于该分的最近档位估算" if not exact else ""),
    }


@app.get("/knowledge/school")
def knowledge_school(name: str, db: Session = Depends(get_db)):
    """聚合一所学校的档案、官方招生计划与历年录取线。

    v0.5：支持用任意已归一别名查询（如「西安89中」「长安一中」），
    并把同一所学校分散在不同写法下的资料合并返回。
    """
    variants = _canonical_map(db, [name])[name]
    alias_row = db.scalar(select(SchoolAlias).where(SchoolAlias.alias == name))
    canonical = alias_row.canonical_name if alias_row else name
    p = db.scalar(
        select(SchoolProfile).where(SchoolProfile.school_name.in_(variants))
        .order_by(SchoolProfile.id).limit(1)
    )
    pl = db.scalar(
        select(EnrollmentPlan).where(EnrollmentPlan.school_name.in_(variants))
        .order_by(EnrollmentPlan.id).limit(1)
    )
    al = db.scalars(
        select(AdmissionScore).where(AdmissionScore.school_name.in_(variants))
        .order_by(AdmissionScore.year, AdmissionScore.id)
    ).all()
    if p is None and pl is None and not al:
        raise HTTPException(status_code=404, detail="知识库中暂无该校资料")
    school = db.scalar(select(School).where(School.name == canonical))
    return {
        "school_name": name,
        "canonical_name": canonical,
        "aliases": sorted(variants - {canonical, name}),
        "school_id": school.id if school else (alias_row.school_id if alias_row else None),
        "has_rank_data": bool(school and (school.data_completeness or "full") == "full"),
        "profile": None if p is None else {
            "address": p.address, "admission_code": p.admission_code,
            "official_site": p.official_site, "phone": p.phone,
            "tuition": p.tuition, "dorm_fee": p.dorm_fee, "boarding": p.boarding,
            "plan_2025": p.plan_2025, "talent_info": p.talent_info,
            "features": p.features, "source_url": p.source_url,
            "credibility": p.credibility,
        },
        "enrollment_plan": None if pl is None else {
            "year": pl.year, "plan_total": pl.plan_total,
            "unified_plan": pl.unified_plan, "directed_plan": pl.directed_plan,
            "sport_talent_plan": pl.sport_talent_plan,
            "art_talent_plan": pl.art_talent_plan,
            "feature_classes": pl.feature_classes,
            "sport_items": pl.sport_items, "art_items": pl.art_items,
            "credibility": pl.credibility,
        },
        "admission_lines": [{
            "year": r.year, "full_score": r.full_score,
            "unified_line": r.unified_line, "score_rate": r.score_rate,
            "source_id": r.source_id, "credibility": r.credibility,
        } for r in al],
        "disclaimer": "录取线为第三方汇总（非官方发布），收费与计划以学校/教育部门当年公示为准。",
    }


@app.get("/knowledge/sources")
def knowledge_sources(db: Session = Depends(get_db)):
    rows = db.scalars(select(DataSource).order_by(DataSource.id)).all()
    return [{
        "id": r.id, "name": r.name, "url": r.url, "kind": r.kind,
        "credibility": r.credibility, "note": r.note, "fetched_at": r.fetched_at,
    } for r in rows]


@app.get("/school-aliases")
def school_aliases(db: Session = Depends(get_db)):
    """人工校名归一映射表（只读，供审计与答辩展示）。"""
    rows = db.scalars(select(SchoolAlias).order_by(SchoolAlias.id)).all()
    return {
        "total": len(rows),
        "items": [{
            "alias": r.alias,
            "canonical_name": r.canonical_name,
            "school_id": r.school_id,
            "kind": r.kind,
            "confidence": r.confidence,
            "reason": r.reason,
        } for r in rows],
        "note": "映射依据见 data/knowledge/school_aliases.csv；confidence=medium 的条目建议复核。",
    }
