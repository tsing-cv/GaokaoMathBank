#!/usr/bin/env bash
# 一键启动:初始化库(若缺)→ 启动 FastAPI
set -e
cd "$(dirname "$0")"
python -m app.init_db
exec uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
