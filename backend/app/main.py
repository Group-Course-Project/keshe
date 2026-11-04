# -*- coding: utf-8 -*-
import json

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    AnalysisReport,
    CandidateProfile,
    EnrollmentRecord,
    MockVolunteer,
    RecommendationResult,
    School,
    SchoolTalent,
)
from .schemas import Candidate, ProfileIn, TrendPoint, VolunteerCheckIn
from .services.backtest import run_backtest
from .services.llm import generate_report
from .services.recommend import recommend
from .services.volunteer import check_volunteers

app = FastAPI(title="西安中考志愿智能分析推荐系统", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _create_profile(
    db: Session,
    predicted_rank: int,
    target_districts: list[str],
    require_dormitory: bool,
    school_type_preference: str,
) -> int:
    profile = CandidateProfile(
        predicted_rank=predicted_rank,
        target_districts=",".join(target_districts),
        require_dormitory=require_dormitory,
        school_type_preference=school_type_preference,
    )
    db.add(profile)
    db.flush()
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


@app.get("/health")
def health():
    return {"status": "ok"}


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
            "talents": [{"category": t.category, "item": t.item} for t in talents],
        })
    return out


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


@app.post("/recommend")
def create_recommendation(profile: ProfileIn, db: Session = Depends(get_db)):
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
def create_report(profile: ProfileIn, db: Session = Depends(get_db)):
    grouped = recommend(
        db,
        predicted_rank=profile.predicted_rank,
        target_districts=profile.target_districts,
        require_dormitory=profile.require_dormitory,
        school_type_preference=profile.school_type_preference,
        top_k=profile.top_k,
    )
    profile_id = profile.profile_id
    if profile_id is None or db.get(CandidateProfile, profile_id) is None:
        profile_id = _create_profile(
            db,
            profile.predicted_rank,
            profile.target_districts,
            profile.require_dormitory,
            profile.school_type_preference,
        )
    _save_recommendations(db, profile_id, grouped)
    preferences = {
        "school_type_preference": profile.school_type_preference,
        "require_dormitory": profile.require_dormitory,
        "target_districts": profile.target_districts,
    }
    content, model, used_fallback = generate_report(
        profile.predicted_rank, grouped, preferences
    )
    report = AnalysisReport(
        profile_id=profile_id,
        model=model,
        prompt_version="v1",
        content=content,
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
def check_volunteer_order(payload: VolunteerCheckIn, db: Session = Depends(get_db)):
    result = check_volunteers(db, payload.predicted_rank, payload.school_ids)
    profile_id = payload.profile_id
    if profile_id is None or db.get(CandidateProfile, profile_id) is None:
        profile_id = _create_profile(db, payload.predicted_rank, [], False, "不限")
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
def list_reports(db: Session = Depends(get_db)):
    rows = db.execute(
        select(AnalysisReport, CandidateProfile)
        .join(CandidateProfile, AnalysisReport.profile_id == CandidateProfile.id)
        .order_by(AnalysisReport.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": r.id,
            "profile_id": p.id,
            "predicted_rank": p.predicted_rank,
            "model": r.model,
            "created_at": r.created_at.isoformat(sep=" ", timespec="seconds") if r.created_at else "",
            "preview": (r.content or "")[:120],
        }
        for r, p in rows
    ]


@app.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(AnalysisReport, report_id)
    if report is None:
        return {"detail": "not found"}
    profile = db.get(CandidateProfile, report.profile_id)
    return {
        "id": report.id,
        "profile_id": report.profile_id,
        "predicted_rank": profile.predicted_rank if profile else None,
        "model": report.model,
        "prompt_version": report.prompt_version,
        "content": report.content,
        "created_at": report.created_at.isoformat(sep=" ", timespec="seconds") if report.created_at else "",
    }


@app.get("/backtest")
def backtest(db: Session = Depends(get_db)):
    return run_backtest(db)
