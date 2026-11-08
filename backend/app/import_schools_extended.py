# -*- coding: utf-8 -*-
"""v0.5 校名归一 + 把知识库中的新学校补进 school 表（幂等、可重复执行）。

背景
----
外部采集的知识库里有 129 个不同的校名，其中只有 57 个能与主推荐库 school
表的 58 所学校精确对上。剩下的 72 个写法经人工核对后分为两类：
  * 2 个是主库已有学校的别名（如「西安89中」→「西安市第八十九中学」）；
  * 70 个归并成 61 所主库没有的学校（含 9 个同校异写）。

本脚本按 data/knowledge/school_aliases.csv 把 61 所学校补进 school 表，
并在 school_alias 表里留下可审计的映射。补进来的学校**没有历年位次记录**，
标记为 knowledge_only / profile_only，不参与冲稳保推荐。

必须在 import_data 之后运行：import_data 会 delete + 重建 school 表并改变主键，
本脚本每次都会按标准校名重新回填 school_id，因此重复执行是安全的。

字段策略（不臆造数据）
----------------------
district   仅在校名或档案地址能明确判定时填写，否则一律「待核实」；
           绝不让新学校冒充城六区学校，避免被 target_districts 误筛中。
school_type 优先取官方招生计划，其次取录取线表的众数，都没有则「待核实」。
has_dormitory 统一 False——原表的该字段由随机 mock 生成，不沿用假值；
           并在 note 里明确标注「住宿信息未采集」。
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select

from .database import SessionLocal
from .migrate import run_migrations
from .models import (
    AdmissionScore,
    EnrollmentPlan,
    EnrollmentRecord,
    School,
    SchoolAlias,
    SchoolProfile,
)

ROOT = Path(__file__).resolve().parents[2]
ALIAS_CSV = ROOT / "data" / "knowledge" / "school_aliases.csv"

# 只按「校名/地址里确实出现的行政区字样」推断，其余保持待核实。
# 顺序即优先级：更具体/更易误判的词必须排前面。
# 例如「泾河新城第一中学」含「新城」，若先匹配「新城」会错判成新城区。
DISTRICT_RULES: list[tuple[str, str]] = [
    ("沣东", "西咸新区"),
    ("泾河", "西咸新区"),
    ("空港", "西咸新区"),
    ("秦汉", "西咸新区"),
    ("西咸", "西咸新区"),
    ("国际港务区", "国际港务区"),
    ("浐灞", "浐灞生态区"),
    ("陆港", "国际港务区"),
    ("碑林", "碑林区"),
    ("新城", "新城区"),
    ("莲湖", "莲湖区"),
    ("雁塔", "雁塔区"),
    ("未央", "未央区"),
    ("灞桥", "灞桥区"),
    ("长安", "长安区"),
    ("航天", "航天基地"),
    ("经开", "经开区"),
    ("高新", "高新区"),
]
UNKNOWN = "待核实"


def read_aliases() -> list[dict[str, str]]:
    """跳过 # 注释行（Write 工具写中文文件会带 BOM，故用 utf-8-sig）。"""
    lines = [
        line
        for line in ALIAS_CSV.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    rows = list(csv.DictReader(lines))
    if not rows or set(("raw_name", "canonical_name", "kind")) - set(rows[0]):
        raise ValueError(f"校名映射表格式异常: {ALIAS_CSV}")
    return rows


def guess_district(canonical: str, all_names: set[str], address: str) -> str:
    """按关键词优先级匹配，保证结果确定（不依赖 set 遍历顺序）。

    档案地址优先，其次在标准名与所有原始写法里找明确的行政区字样。
    """
    haystacks = ([address] if address else []) + [canonical] + sorted(all_names)
    for key, value in DISTRICT_RULES:
        if any(key in text for text in haystacks):
            return value
    return UNKNOWN


def run() -> dict[str, int]:
    run_migrations()
    rows = read_aliases()

    # 每个标准校名关联的所有原始写法（canonical 自身也是知识表里的名字）
    names_of: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r["kind"] == "new":
            names_of[r["canonical_name"]].add(r["raw_name"])
            names_of[r["canonical_name"]].add(r["canonical_name"])

    db = SessionLocal()
    stats = Counter()
    try:
        for canonical, names in sorted(names_of.items()):
            plans = db.scalars(
                select(EnrollmentPlan).where(EnrollmentPlan.school_name.in_(names))
            ).all()
            lines = db.scalars(
                select(AdmissionScore).where(AdmissionScore.school_name.in_(names))
            ).all()
            profiles = db.scalars(
                select(SchoolProfile).where(SchoolProfile.school_name.in_(names))
            ).all()

            nature = next((p.school_nature for p in plans if p.school_nature), "")
            if not nature:
                tally = Counter(x.school_nature for x in lines if x.school_nature)
                nature = tally.most_common(1)[0][0] if tally else ""
            nature = nature if nature in ("公办", "民办") else UNKNOWN

            levels = Counter(x.school_level for x in lines if x.school_level)
            level = levels.most_common(1)[0][0] if levels else ""
            years = sorted({x.year for x in lines})
            address = next((p.address for p in profiles if p.address), "")
            district = guess_district(canonical, names, address)

            bits: list[str] = []
            if plans:
                total = next((p.plan_total for p in plans if p.plan_total), None)
                bits.append("2025官方招生计划" + (f"{total}人" if total else ""))
            if lines:
                span = f"{years[0]}–{years[-1]}" if years else ""
                bits.append(f"{span}录取线{len(lines)}条（第三方汇总）")
                if level:
                    bits.append(level)
            if profiles:
                bits.append("校园档案")
            source_summary = "；".join(bits)
            completeness = "knowledge_only" if (plans or lines) else "profile_only"

            note = (
                f"v0.5人工校名归一补录；原始写法{len(names)}种；"
                "住宿信息未采集；无历年位次，不参与冲稳保推荐"
            )[:200]

            school = db.scalar(select(School).where(School.name == canonical))
            if school is None:
                school = School(name=canonical)
                db.add(school)
                stats["新增学校"] += 1
            else:
                stats["已存在跳过"] += 1
            school.district = district
            school.school_type = nature
            school.has_dormitory = False
            school.note = note
            school.source_summary = source_summary[:300]
            # 已有位次记录的学校永远是 full，避免误降级原 58 校
            has_rank = db.scalar(
                select(EnrollmentRecord.id).where(EnrollmentRecord.school_id == school.id).limit(1)
            ) if school.id else None
            school.data_completeness = "full" if has_rank else completeness

        db.flush()

        # 回填 school_id：import_data 重建 school 表会改变主键，所以每次都重算
        name_to_id = {s.name: s.id for s in db.scalars(select(School)).all()}
        for r in rows:
            existing = db.scalar(
                select(SchoolAlias).where(SchoolAlias.alias == r["raw_name"])
            )
            if existing is None:
                existing = SchoolAlias(alias=r["raw_name"])
                db.add(existing)
                stats["新增别名"] += 1
            else:
                stats["更新别名"] += 1
            existing.canonical_name = r["canonical_name"]
            existing.school_id = name_to_id.get(r["canonical_name"])
            existing.kind = r["kind"]
            existing.confidence = r["confidence"] or "high"
            existing.reason = r["reason"]

        db.commit()

        # 确保原 58 校没有被误改（防御性校验）
        wrong = db.scalar(
            select(School.id).where(
                School.data_completeness != "full",
                School.id.in_(select(EnrollmentRecord.school_id)),
            ).limit(1)
        )
        total_schools = db.query(School).count()
        full = db.query(School).filter(School.data_completeness == "full").count()
        stats["学校总数"] = total_schools
        stats["有位次学校"] = full
        stats["别名总数"] = db.query(SchoolAlias).count()
        if wrong:
            raise RuntimeError(f"有位次记录的学校被标成了非 full，school.id={wrong}")
        return dict(stats)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = run()
    for key, value in sorted(result.items()):
        print(f"  {key}: {value}")
