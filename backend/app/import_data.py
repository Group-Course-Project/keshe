# -*- coding: utf-8 -*-
"""把 data/processed 的两张 CSV 导入 SQLite。"""
import csv

from .config import PROCESSED_DIR
from .database import Base, SessionLocal, engine
from .models import EnrollmentRecord, School


def run():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        db.query(EnrollmentRecord).delete()
        db.query(School).delete()
        db.commit()

        name_to_id = {}
        with open(PROCESSED_DIR / "schools.csv", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                school = School(
                    name=row["学校名称"],
                    district=row["城区"],
                    school_type=row["办学性质"],
                    has_dormitory=row["是否住宿"].strip() in ("1", "true", "True", "是"),
                    note=row.get("备注", ""),
                )
                db.add(school)
                db.flush()
                name_to_id[school.name] = school.id

        with open(PROCESSED_DIR / "enrollment_records.csv", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                raw_rank = row["最低位次"].strip()
                min_rank = int(raw_rank) if raw_rank != "" else None
                db.add(EnrollmentRecord(
                    school_id=name_to_id[row["学校名称"]],
                    year=int(row["年份"]),
                    min_rank=min_rank,
                    rank_status=row["位次状态"],
                    raw_value=row["原始值"],
                ))
        db.commit()
        print("导入完成：学校", db.query(School).count(), "，位次记录", db.query(EnrollmentRecord).count())
    finally:
        db.close()


if __name__ == "__main__":
    run()
