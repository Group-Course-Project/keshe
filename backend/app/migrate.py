# -*- coding: utf-8 -*-
"""轻量 SQLite 迁移。

SQLAlchemy 的 ``create_all`` 只建缺失的表，不会给已存在的表补列。
项目早期的 ``data/app.db`` 里已有画像与报告数据，直接删库会丢历史记录，
因此这里在应用启动时用 PRAGMA 检查并按需 ALTER TABLE ADD COLUMN。

新增表由 create_all 负责；新增列由 _ADD_COLUMNS 负责。两者都是幂等的。
"""
from __future__ import annotations

from sqlalchemy import text

from . import models  # noqa: F401 —— 触发所有模型注册到 Base.metadata
from .database import Base, engine

_ADD_COLUMNS: list[tuple[str, str, str]] = [
    ("candidate_profile", "user_id", "INTEGER"),
    ("analysis_report", "user_id", "INTEGER"),
    # v0.5 校名归一：给已有 school 表补数据完整度标记，旧库默认视为 full。
    ("school", "data_completeness", "VARCHAR(20) DEFAULT 'full'"),
    ("school", "source_summary", "VARCHAR(300) DEFAULT ''"),
]


def run_migrations() -> list[str]:
    """建新表 + 补旧列，返回实际执行的动作列表，便于日志与测试观察。"""
    actions: list[str] = []
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        for table, column, coltype in _ADD_COLUMNS:
            if table not in tables:
                continue
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
                actions.append(f"ADD COLUMN {table}.{column}")

    return actions


if __name__ == "__main__":
    done = run_migrations()
    print("迁移完成：", done or "无待执行变更")
