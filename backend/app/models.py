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


class CandidateProfile(Base):
    __tablename__ = "candidate_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(50), default="")
    predicted_rank: Mapped[int] = mapped_column(Integer)
    target_districts: Mapped[str] = mapped_column(Text, default="")
    require_dormitory: Mapped[bool] = mapped_column(Boolean, default=False)
    school_type_preference: Mapped[str] = mapped_column(String(20), default="不限")
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
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class MockVolunteer(Base):
    __tablename__ = "mock_volunteer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id"), index=True)
    order_no: Mapped[int] = mapped_column(Integer)
    school_id: Mapped[int] = mapped_column(ForeignKey("school.id"))
    strategy: Mapped[str] = mapped_column(String(10))
    gradient_check_json: Mapped[str] = mapped_column(Text, default="[]")
