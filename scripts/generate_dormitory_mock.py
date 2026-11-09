# -*- coding: utf-8 -*-
"""生成 school.has_dormitory 的 0/1 模拟值（明确标注：不是真实数据）。

重要说明
--------
本字段按项目约定就是**模拟数据**：随机生成 0 / 1 代表「是否提供住宿」，
不代表任何一所学校的真实住宿情况，**不可作为择校依据**。
前端所有展示该字段的位置都必须带「模拟数据」标记，不能写成事实结论。

为什么单独成一个脚本
--------------------
原先随机值藏在 scripts/clean_data.py 的清洗流程里，容易被误认为是真实采集结果。
现在把生成逻辑集中到这里，clean_data.py 只写占位 0，由本脚本统一生成并同时写回：
  - data/processed/schools.csv 的「是否住宿」列（import_data.py 重建数据库时读取）
  - data/app.db 的 school.has_dormitory 列（当前运行中的数据库）

用法（项目根目录）：
    backend\\.venv\\Scripts\\python.exe scripts\\generate_dormitory_mock.py
    ... --seed 2026          # 换一批随机值
    ... --random-seed        # 用系统随机种子，结果不再可复现

默认 seed=42，与旧 clean_data.py 一致，保证每次启动结果稳定、可答辩复现。
本脚本只改 0/1 一列，不新增/删除学校，不影响位次与冲稳保推荐结果。
"""
from __future__ import annotations

import argparse
import csv
import random
import secrets
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "processed" / "schools.csv"
DB_PATH = ROOT / "data" / "app.db"
DEFAULT_SEED = 42
DORMITORY_HEADER = "是否住宿"


def generate(names: list[str], seed: int) -> dict[str, int]:
    """按校名列表顺序生成 0/1；固定 seed 时可复现。"""
    rng = random.Random(seed)
    return {name: rng.randint(0, 1) for name in names}


def write_csv(rows: list[dict], header: list[str], values: dict[str, int]) -> None:
    for row in rows:
        row[DORMITORY_HEADER] = values[row["学校名称"]]
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def write_db(values: dict[str, int]) -> tuple[int, list[str]]:
    if not DB_PATH.exists():
        return 0, []
    conn = sqlite3.connect(DB_PATH)
    try:
        known = {r[0] for r in conn.execute("select name from school")}
        for name, value in values.items():
            if name in known:
                conn.execute(
                    "update school set has_dormitory = ? where name = ?", (value, name)
                )
        conn.commit()
        return len(known & values.keys()), sorted(values.keys() - known)
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="生成住宿字段的 0/1 模拟值")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED, help="随机种子（默认 42）")
    ap.add_argument("--random-seed", action="store_true", help="改用系统随机种子")
    args = ap.parse_args()
    seed = secrets.randbelow(2**31) if args.random_seed else args.seed

    if not CSV_PATH.exists():
        raise SystemExit(
            f"找不到 {CSV_PATH}，请先运行 scripts/clean_data.py 生成 processed 数据。"
        )
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    if DORMITORY_HEADER not in header or not rows:
        raise SystemExit(f"{CSV_PATH} 缺少「{DORMITORY_HEADER}」列或没有数据行。")

    values = generate([r["学校名称"] for r in rows], seed)
    write_csv(rows, header, values)
    updated, missing = write_db(values)

    ones = sum(values.values())
    print("住宿模拟值生成完成（模拟数据，不代表学校真实情况，不可作为择校依据）")
    print(f"  seed={seed} | CSV={CSV_PATH.name} {len(rows)} 行 | DB 更新 {updated} 校")
    print(f"  1（模拟·提供）{ones} 所 / 0（模拟·不提供）{len(values) - ones} 所")
    if missing:
        print(f"  CSV 中 {len(missing)} 所不在 school 表，已跳过：{missing[:3]}")
    if not DB_PATH.exists():
        print("  提示：data/app.db 尚不存在，下次初始化数据库时会从 CSV 读入。")


if __name__ == "__main__":
    main()
