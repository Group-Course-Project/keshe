@echo off
REM One-click dev launcher for the Xi'an Zhongkao advisor (ASCII only, Windows).
setlocal
set ROOT=%~dp0..
cd /d "%ROOT%"
set ROOT=%CD%

if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/6] Creating Python venv and installing backend deps...
  python -m venv backend\.venv
  call backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
) else (
  echo [1/6] Python venv already exists, skip.
)

if not exist "backend\.env" (
  echo [2/6] Creating backend\.env from template with an empty API key.
  copy /y "backend\.env.example" "backend\.env" >nul
) else (
  echo [2/6] backend\.env already exists, skip.
)

if not exist "data\app.db" (
  echo [3/6] Initializing SQLite database...
  cd /d "%ROOT%\backend"
  call .venv\Scripts\python.exe -c "from app.import_data import run; run()"
  call .venv\Scripts\python.exe -c "from app.import_talent import run; run()"
  cd /d "%ROOT%"
) else (
  echo [3/6] data\app.db already exists, skip base import.
)

echo [4/6] Importing collected knowledge base (idempotent)...
cd /d "%ROOT%\backend"
call .venv\Scripts\python.exe -m app.import_knowledge
cd /d "%ROOT%"

REM 58-school scope: school_aliases.csv now only maps aliases of existing schools.
REM import_schools_extended is intentionally NOT run (it would re-add 61 incomplete schools).

echo [5/6] Generating mock dormitory flags (0/1, NOT real school data)...
cd /d "%ROOT%"
call backend\.venv\Scripts\python.exe scripts\generate_dormitory_mock.py

if not exist "frontend\node_modules\vite\bin\vite.js" (
  echo [6/6] Installing frontend dependencies...
  cd /d "%ROOT%\frontend"
  call npm install
  cd /d "%ROOT%"
) else (
  echo [6/6] frontend deps already exist, skip.
)

echo Starting backend (8000) and frontend (5173) in two windows...
cd /d "%ROOT%\backend"
start "keshe-backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
cd /d "%ROOT%\frontend"
start "keshe-frontend" cmd /k "node node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173"

echo.
echo Frontend : http://127.0.0.1:5173
echo API docs : http://127.0.0.1:8000/docs
echo Knowledge: GET http://127.0.0.1:8000/knowledge/summary
echo Aliases  : GET http://127.0.0.1:8000/school-aliases
echo Try predicted_rank = 12000 to see all three tiers (chong / wen / bao).
echo Close the two service windows to stop.
