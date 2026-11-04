# -*- coding: utf-8 -*-
"""解析两份招生计划 PDF 的体育类/艺术类特长生项目，写入 school_talent 表。"""
import re

import pdfplumber

from .config import BASE_DIR
from .database import Base, SessionLocal, engine
from .models import School, SchoolTalent

PDFS = [
    BASE_DIR / "data" / "raw" / "2025城六区公办招生计划.pdf",
    BASE_DIR / "data" / "raw" / "2025城六区民办招生计划.pdf",
]


def _clean_name(raw: str) -> str:
    raw = (raw or "").replace("\n", "").strip()
    return re.sub(r"\(.*\)$", "", raw).strip()


def _split_items(raw: str) -> list[str]:
    raw = (raw or "").replace("\n", "").replace("　", "").strip()
    raw = raw.rstrip("、，,")
    parts = re.split(r"[、，,]", raw)
    norm = {
        "乒乒球": "乒乓球",
        "乓乓球": "乒乓球",
        "棒（垒）球": "棒（垒）球",
        "戏剧（曲）": "戏剧（曲）",
    }
    return [norm.get(p.strip(), p.strip()) for p in parts if p.strip()]


def run():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        db.query(SchoolTalent).delete()
        db.commit()

        school_by_name = {s.name: s for s in db.query(School).all()}
        inserted = 0
        unmatched = set()

        for path in PDFS:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if not tables:
                        continue
                    for row in tables[0]:
                        first = (row[0] or "").replace("\n", "").strip()
                        if not re.fullmatch(r"\d+", first):
                            continue
                        name = _clean_name(row[1])
                        sports = _split_items(row[15]) if len(row) > 15 else []
                        arts = _split_items(row[16]) if len(row) > 16 else []
                        school = school_by_name.get(name)
                        if school is None:
                            unmatched.add(name)
                            continue
                        for item in sports:
                            db.add(SchoolTalent(school_id=school.id, category="体育", item=item))
                            inserted += 1
                        for item in arts:
                            db.add(SchoolTalent(school_id=school.id, category="艺术", item=item))
                            inserted += 1
        db.commit()
        print("特长生项目导入:", inserted, "条")
        if unmatched:
            print("未匹配到库内学校的名称:", sorted(unmatched))
    finally:
        db.close()


if __name__ == "__main__":
    run()
