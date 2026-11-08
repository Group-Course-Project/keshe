# -*- coding: utf-8 -*-
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class School(Base):
    __tablename__ = "school"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    district: Mapped[str] = mapped_column(String(30), index=True)
    school_type: Mapped[str] = mapped_column(String(10))  # 公办 / 民办
    has_dormitory: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(200), default="")
    # v0.5：区分「有历年位次、可参与冲稳保」与「仅外部知识、不参与推荐」两类学校。
    # full=有 enrollment_record；knowledge_only=有招生计划/录取线但无位次；profile_only=仅有校园档案。
    data_completeness: Mapped[str] = mapped_column(String(20), default="full", index=True)
    source_summary: Mapped[str] = mapped_column(String(300), default="")

    records: Mapped[list["EnrollmentRecord"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )


class EnrollmentRecord(Base):
    __tablename__ = "enrollment_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    min_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_status: Mapped[str] = mapped_column(String(20), default="正常")
    raw_value: Mapped[str] = mapped_column(String(50), default="")

    school: Mapped["School"] = relationship(back_populates="records")


class SchoolTalent(Base):
    __tablename__ = "school_talent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), index=True)
    category: Mapped[str] = mapped_column(String(10), index=True)  # 体育 / 艺术
    item: Mapped[str] = mapped_column(String(30), index=True)


class AppUser(Base):
    """本地账号。密码只存 PBKDF2 派生值，不存明文。"""

    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(50), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class AuthSession(Base):
    """服务端会话令牌，支持登出即失效。"""

    __tablename__ = "auth_session"

    token: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[DateTime] = mapped_column(DateTime, index=True)


class VolunteerPlan(Base):
    """一套可保存/对比/分享的志愿方案快照。"""

    __tablename__ = "volunteer_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    profile_json: Mapped[str] = mapped_column(Text, default="{}")
    volunteers_json: Mapped[str] = mapped_column(Text, default="[]")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    share_token: Mapped[str | None] = mapped_column(
        String(48), unique=True, index=True, nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class CandidateProfile(Base):
    __tablename__ = "candidate_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(50), default="")
    predicted_rank: Mapped[int] = mapped_column(Integer)
    target_districts: Mapped[str] = mapped_column(Text, default="")
    require_dormitory: Mapped[bool] = mapped_column(Boolean, default=False)
    school_type_preference: Mapped[str] = mapped_column(String(20), default="不限")
    # 可空：未登录时产生的匿名画像保持兼容
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id"), nullable=True, index=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class RecommendationResult(Base):
    __tablename__ = "recommendation_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id"), index=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"), index=True)
    strategy: Mapped[str] = mapped_column(String(10))  # 冲 / 稳 / 保
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class AnalysisReport(Base):
    __tablename__ = "analysis_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id"), index=True)
    model: Mapped[str] = mapped_column(String(50), default="")
    prompt_version: Mapped[str] = mapped_column(String(20), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    # 冗余存储便于按用户直接过滤，避免每次 join
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id"), nullable=True, index=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class MockVolunteer(Base):
    __tablename__ = "mock_volunteer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id"), index=True)
    order_no: Mapped[int] = mapped_column(Integer)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"))
    strategy: Mapped[str] = mapped_column(String(10))
    gradient_check_json: Mapped[str] = mapped_column(Text, default="[]")


# ---------------------------------------------------------------- 外部采集知识库
# 这些表与原有 school / enrollment_record 相互独立：不改动原表结构，也不参与冲稳保算法，
# 只作为「学校档案 / 历年分数线 / 分数转位次」的补充数据源，供查询接口与 AI 报告上下文使用。
# 每条记录都保留来源 ID 与可信等级，详见 docs/西安中考数据知识库.md。


class ControlLine(Base):
    """历年城六区录取最低控制线。"""

    __tablename__ = "control_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    unit: Mapped[str] = mapped_column(String(30), default="城六区")
    full_score: Mapped[int] = mapped_column(Integer)
    general_line: Mapped[float | None] = mapped_column(Float, nullable=True)
    talent_line: Mapped[float | None] = mapped_column(Float, nullable=True)
    integrated_line: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[str] = mapped_column(String(10), default="")
    credibility: Mapped[str] = mapped_column(String(2), default="")
    note: Mapped[str] = mapped_column(Text, default="")


class AdmissionScore(Base):
    """逐年逐校统招线 / 定转统线（第三方汇总，非官方逐校发布）。"""

    __tablename__ = "admission_score"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_name: Mapped[str] = mapped_column(String(100), index=True)
    raw_name: Mapped[str] = mapped_column(String(100), default="")
    match_status: Mapped[str] = mapped_column(String(30), default="")
    year: Mapped[int] = mapped_column(Integer, index=True)
    full_score: Mapped[int] = mapped_column(Integer)
    unified_line: Mapped[float | None] = mapped_column(Float, nullable=True)
    transfer_line: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # 百分数，如 95.81
    school_level: Mapped[str] = mapped_column(String(20), default="")
    school_nature: Mapped[str] = mapped_column(String(10), default="")
    batch: Mapped[str] = mapped_column(String(20), default="")
    source_id: Mapped[str] = mapped_column(String(10), default="")
    credibility: Mapped[str] = mapped_column(String(2), default="")
    cross_check: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(Text, default="")


class ScoreRankMap(Base):
    """一分一段表：分数 → 城六区累计位次。"""

    __tablename__ = "score_rank_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit: Mapped[str] = mapped_column(String(30), default="城六区")
    year: Mapped[int] = mapped_column(Integer, index=True)
    full_score: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer, index=True)
    cumulative_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_id: Mapped[str] = mapped_column(String(10), default="")
    credibility: Mapped[str] = mapped_column(String(2), default="")
    note: Mapped[str] = mapped_column(String(100), default="")


class EnrollmentPlan(Base):
    """教育局 2025 招生计划原件解析结果（官方 A 级）。"""

    __tablename__ = "enrollment_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_name: Mapped[str] = mapped_column(String(100), index=True)
    raw_name: Mapped[str] = mapped_column(String(100), default="")
    match_status: Mapped[str] = mapped_column(String(30), default="")
    school_nature: Mapped[str] = mapped_column(String(10), default="")
    year: Mapped[int] = mapped_column(Integer, index=True)
    plan_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unified_plan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    directed_plan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sport_talent_plan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    art_talent_plan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feature_classes: Mapped[str] = mapped_column(Text, default="")
    sport_items: Mapped[str] = mapped_column(Text, default="")
    art_items: Mapped[str] = mapped_column(Text, default="")
    single_plan: Mapped[str] = mapped_column(Text, default="")
    source_id: Mapped[str] = mapped_column(String(10), default="")
    credibility: Mapped[str] = mapped_column(String(2), default="")
    note: Mapped[str] = mapped_column(Text, default="")


class SchoolProfile(Base):
    """学校档案：地址、收费、食宿、办学特色（来自学校署名招生简章）。"""

    __tablename__ = "school_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_name: Mapped[str] = mapped_column(String(100), index=True)
    raw_name: Mapped[str] = mapped_column(String(100), default="")
    match_status: Mapped[str] = mapped_column(String(30), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    admission_code: Mapped[str] = mapped_column(String(20), default="")
    official_site: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str] = mapped_column(String(100), default="")
    tuition: Mapped[str] = mapped_column(Text, default="")
    dorm_fee: Mapped[str] = mapped_column(String(100), default="")
    boarding: Mapped[str] = mapped_column(Text, default="")
    plan_2025: Mapped[str] = mapped_column(Text, default="")
    talent_info: Mapped[str] = mapped_column(Text, default="")
    features: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    credibility: Mapped[str] = mapped_column(String(2), default="")
    fetched_at: Mapped[str] = mapped_column(String(20), default="")


class SchoolAlias(Base):
    """人工核对的校名归一映射：原始校名 → 唯一标准校名 → school.id。

    种源文件为 data/knowledge/school_aliases.csv，每条都写明判断依据与置信度。
    kind=existing 表示只是主库已有学校的别名；kind=new 表示映射到新增学校。
    school_id 在导入后回填，便于 /knowledge/* 接口按任意别名聚合资料。
    """

    __tablename__ = "school_alias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String(120), index=True)
    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("school.id"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), default="new")
    confidence: Mapped[str] = mapped_column(String(10), default="high")
    reason: Mapped[str] = mapped_column(Text, default="")


class DataSource(Base):
    """数据源清单与可信等级。"""

    __tablename__ = "data_source"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(40), default="")
    credibility: Mapped[str] = mapped_column(String(2), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    fetched_at: Mapped[str] = mapped_column(String(20), default="")
