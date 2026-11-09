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


# ---------- 用户体系 ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=30, description="登录名，3-30 位")
    password: str = Field(min_length=6, max_length=64, description="密码，至少 6 位")
    display_name: str = Field(default="", max_length=30, description="显示昵称，可留空")


class LoginIn(BaseModel):
    username: str
    password: str


# ---------- 多套志愿方案 ----------
class PlanIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    profile: dict = Field(default_factory=dict, description="考生画像快照")
    volunteers: list[dict] = Field(default_factory=list, description="按顺序排列的志愿学校")
    summary: dict = Field(default_factory=dict, description="冲稳保数量、梯度校验结果等")


class PlanUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    profile: dict | None = None
    volunteers: list[dict] | None = None
    summary: dict | None = None


# ---------- 学校对比 ----------
class CompareIn(BaseModel):
    school_ids: list[int] = Field(min_length=1, max_length=4, description="最多对比 4 所学校")
