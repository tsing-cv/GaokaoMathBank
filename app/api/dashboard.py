"""首页仪表盘:总量统计 + 按年份聚合的覆盖一览(卷名可点直达)。"""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Paper, Question, get_db

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates"))

# 覆盖区块每年最多展示的卷数,超出折叠为"等N卷"链接(1977 年有 79 卷)
CHIPS_PER_YEAR = 8


@router.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    paper_total = db.scalar(select(func.count(Paper.id)))
    q_total = db.scalar(select(func.count(Question.id)))
    # 按年聚合:卷列表(id+name)与题数合计——旧"年份×省份"矩阵有 80+ 列
    # (province 曾含拼音 key),超出视口且无一链接可点,2026-09 重构。
    by_year: dict[int, dict] = {}
    for p in db.execute(
        select(Paper).order_by(Paper.year.desc(), Paper.name)
    ).scalars():
        y = by_year.setdefault(p.year, {"papers": [], "n_q": 0})
        y["papers"].append({"id": p.id, "name": p.name})
        y["n_q"] += p.question_count or 0
    years = [{"year": y, **d} for y, d in sorted(by_year.items(), reverse=True)]
    return templates.TemplateResponse(request, "index.html", {
        "paper_total": paper_total or 0,
        "q_total": q_total or 0,
        "years": years,
        "chips_max": CHIPS_PER_YEAR,
    })
