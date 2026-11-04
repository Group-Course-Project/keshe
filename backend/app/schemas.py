# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field


class ProfileIn(BaseModel):
    predicted_rank: int = Field(gt=0, description="考生预估位次")
    target_districts: list[str] = Field(default_factory=list, description="目标城区，空=不限")
    require_dormitory: bool = Field(default=False, description="是否必须提供住宿")
    school_type_preference: str = Field(
        default="不限", description="不限 / 公办 / 民办"
    )
    top_k: int = Field(default=8, ge=1, le=30, description="每档返回数量")
    profile_id: int | None = Field(default=None, description="可选，关联已有画像")


class TrendPoint(BaseModel):
    year: int
    min_rank: int | None
    status: str


class TalentItem(BaseModel):
    category: str
    item: str


class Candidate(BaseModel):
    school_id: int
    name: str
    district: str
    school_type: str
    has_dormitory: bool
    strategy: str
    match_score: float
    ref_rank: int | None
    ref_year: int | None
    years_available: int
    reasons: list[str]
    talents: list[TalentItem] = Field(default_factory=list)


class VolunteerCheckIn(BaseModel):
    predicted_rank: int = Field(gt=0)
    school_ids: list[int]
    profile_id: int | None = Field(default=None)
