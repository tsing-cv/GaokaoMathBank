"""首页仪表盘:总量统计 + 年份×省份覆盖。"""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Paper, Question, get_db

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    paper_total = db.scalar(select(func.count(Paper.id)))
    q_total = db.scalar(select(func.count(Question.id)))
    # 年份×卷种覆盖矩阵
    rows = db.execute(
        select(Paper.year, Paper.province, func.count(Paper.id))
        .group_by(Paper.year, Paper.province)
    ).all()
    coverage: dict[int, dict[str, int]] = {}
    for year, prov, cnt in rows:
        coverage.setdefault(year, {})[prov] = cnt
    return templates.TemplateResponse(request, "index.html", {
        "paper_total": paper_total or 0,
        "q_total": q_total or 0,
        "coverage": coverage,
        "provinces": sorted({p for _, p, _ in rows}),
    })
