# -*- coding: utf-8 -*-
"""把 data/knowledge/*.csv 导入外部采集知识库表（幂等，可重复执行）。

用法（在 backend 目录下）：
    python -m app.import_knowledge

与 import_data.py / import_talent.py 的区别：
  - 不改动 school / enrollment_record / school_talent 三张原表，冲稳保推荐结果不受影响。
  - 每次先清空 6 张知识库表再全量写入，避免重复数据。
  - 只导入 data/knowledge 下的文件；这些文件由 scripts/build_knowledge_dataset.py 生成。
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from .config import BASE_DIR
from .database import SessionLocal, engine
from .migrate import run_migrations
from .models import (
    AdmissionScore,
    ControlLine,
    DataSource,
    EnrollmentPlan,
    SchoolProfile,
    ScoreRankMap,
)

K = BASE_DIR / "data" / "knowledge"


def _f(v):
    """转 float，空值/非数值返回 None。"""
    s = (v or "").strip().rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None


def _i(v):
    f = _f(v)
    return int(f) if f is not None else None


def _rows(name: str) -> list[dict]:
    path = K / name
    if not path.exists():
        raise FileNotFoundError(f"缺少 {path}，请先运行 python scripts/build_knowledge_dataset.py")
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def run() -> dict[str, int]:
    run_migrations()  # 确保 6 张新表已创建
    db = SessionLocal()
    counts: dict[str, int] = {}
    try:
        # ---- 清空（保持导入幂等）
        for model in (ControlLine, AdmissionScore, ScoreRankMap,
                      EnrollmentPlan, SchoolProfile, DataSource):
            db.query(model).delete()
        db.flush()

        # ---- 历年控制线
        for r in _rows("control_lines_2020_2025.csv"):
            db.add(ControlLine(
                year=_i(r["年份"]), unit=r["招生单元"], full_score=_i(r["总分满分"]),
                general_line=_f(r["普高录取控制线"]), talent_line=_f(r["体艺特长生控制线"]),
                integrated_line=_f(r["综合高中班控制线"]), source_id=r["来源ID"],
                credibility=r["可信等级"], note=r["备注"],
            ))
        counts["control_line"] = len(_rows("control_lines_2020_2025.csv"))

        # ---- 逐年逐校录取线
        al = _rows("admission_lines_2020_2025.csv")
        for r in al:
            db.add(AdmissionScore(
                school_name=r["标准校名"], raw_name=r["原始校名"],
                match_status=r["匹配状态"], year=_i(r["年份"]),
                full_score=_i(r["总分满分"]), unified_line=_f(r["统招线"]),
                transfer_line=_f(r["定转统线"]), score_rate=_f(r["得分率"]),
                school_level=r["学校属性"], school_nature=r["办学性质"],
                batch=r["招生批次"], source_id=r["来源ID"],
                credibility=r["可信等级"], cross_check=r["交叉校验值"], note=r["备注"],
            ))
        counts["admission_score"] = len(al)

        # ---- 一分一段
        sr = _rows("score_rank_map_2025.csv")
        for r in sr:
            score = re.sub(r"\D", "", r["中考成绩"])
            db.add(ScoreRankMap(
                unit=r["招生单元"], year=_i(r["年份"]), full_score=_i(r["总分满分"]),
                score=int(score) if score else None,
                cumulative_rank=_i(r["城六区累计位次"]), ratio=_f(r["位比%"]),
                source_id=r["来源ID"], credibility=r["可信等级"], note=r["备注"],
            ))
        counts["score_rank_map"] = len(sr)

        # ---- 官方招生计划
        ep = _rows("enrollment_plan_2025.csv")
        for r in ep:
            db.add(EnrollmentPlan(
                school_name=r["标准校名"], raw_name=r["PDF原始校名"],
                match_status=r["匹配状态"], school_nature=r["办学性质"],
                year=_i(r["年份"]), plan_total=_i(r["招生计划总数"]),
                unified_plan=_i(r["统招生计划"]), directed_plan=_i(r["定向生计划"]),
                sport_talent_plan=_i(r["体育特长生计划"]),
                art_talent_plan=_i(r["艺术特长生计划"]),
                feature_classes=r["特色班类别"], sport_items=r["体育类特长项目"],
                art_items=r["艺术类特长项目"], single_plan=r["单列计划"],
                source_id=r["来源ID"], credibility=r["可信等级"], note=r["备注"],
            ))
        counts["enrollment_plan"] = len(ep)

        # ---- 校园档案
        sp = _rows("school_profiles.csv")
        for r in sp:
            db.add(SchoolProfile(
                school_name=r["标准校名"], raw_name=r["原始校名"],
                match_status=r["匹配状态"], address=r["学校地址"],
                admission_code=r["招生代码"], official_site=r["官网"],
                phone=r["咨询电话"], tuition=r["学费"], dorm_fee=r["住宿费"],
                boarding=r["食宿条件"], plan_2025=r["2025招生计划"],
                talent_info=r["特长生信息"], features=r["办学特色/简介"],
                source_url=r["来源URL"], credibility=r["可信等级"],
                fetched_at=r["抓取日期"],
            ))
        counts["school_profile"] = len(sp)

        # ---- 数据源
        ds = _rows("data_sources.csv")
        for r in ds:
            db.add(DataSource(
                id=r["来源ID"], name=r["来源名称"], url=r["URL"],
                kind=r["类型"], credibility=r["可信等级"],
                note=r["说明"], fetched_at=r["抓取日期"],
            ))
        counts["data_source"] = len(ds)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return counts


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    result = run()
    print("知识库导入完成：")
    for k, v in result.items():
        print(f"  {k:<20} {v:>4} 行")
