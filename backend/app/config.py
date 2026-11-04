# -*- coding: utf-8 -*-
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.db'}"
BACKEND_DIR = BASE_DIR / "backend"
