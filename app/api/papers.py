"""试卷库:/papers 列表筛选分页 + /paper/{id} 整卷视图 + 原卷 PDF。"""
import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Paper, Question, get_db
from .. import RAW_DIR

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates"))

PAGE_SIZE = 30


@router.get("/papers")
async def papers(request: Request, db: Session = Depends(get_db),
                 year: int | None = None, province: str | None = None,
                 exam_type: str | None = None, subject: str | None = None,
                 page: int = 1, page_size: int = PAGE_SIZE):
    """列表页:筛选 + 分页(年份倒序,同年后按省份)。"""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    cond = []
    if year:
        cond.append(Paper.year == year)
    if province:
        cond.append(Paper.province == province)
    if exam_type:
        cond.append(Paper.exam_type == exam_type)
    if subject:
        cond.append(Paper.subject == subject)
    total = db.scalar(select(func.count(Paper.id)).where(*cond)) or 0
    rows = db.execute(
        select(Paper).where(*cond)
        .order_by(Paper.year.desc(), Paper.province)
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    # 筛选项(全库口径,不受当前筛选影响)
    years = [y for y, in db.execute(
        select(Paper.year).distinct().order_by(Paper.year.desc()))]
    provinces = [p for p, in db.execute(
        select(Paper.province).distinct().order_by(Paper.province))]
    subjects = [s for s, in db.execute(
        select(Paper.subject).distinct().order_by(Paper.subject))]
    return templates.TemplateResponse(request, "papers.html", {
        "papers": rows, "total": total, "page": page,
        "pages": max(math.ceil(total / page_size), 1),
        "years": years, "provinces": provinces, "subjects": subjects,
        "cur": {"year": year or "", "province": province or "",
                "exam_type": exam_type or "", "subject": subject or ""},
    })


@router.get("/paper/{pid}")
async def paper_detail(request: Request, pid: int,
                       db: Session = Depends(get_db)):
    """整卷视图:题目按序号排,答案/解析模板内折叠。"""
    paper = db.get(Paper, pid)
    if not paper:
        raise HTTPException(404)
    questions = db.execute(
        select(Question).where(Question.paper_id == pid)
        .order_by(Question.seq)).scalars().all()
    return templates.TemplateResponse(request, "paper_detail.html", {
        "paper": paper, "questions": questions,
    })


@router.get("/paper/{pid}/pdf")
async def paper_pdf(pid: int, db: Session = Depends(get_db)):
    """原卷 PDF 下载(路径必须位于 RAW_DIR 内,防目录穿越)。"""
    paper = db.get(Paper, pid)
    if not paper or not paper.pdf_path:
        raise HTTPException(404)
    f = Path(paper.pdf_path).resolve()
    if not f.is_file():
        raise HTTPException(404)
    try:
        f.relative_to(RAW_DIR.resolve())
    except ValueError:
        raise HTTPException(404)
    return FileResponse(f, media_type="application/pdf",
                        filename=f.name)
