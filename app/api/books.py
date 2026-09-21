"""汇编成册页:/books 列表 + 三种生成入口 + 下载。"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from ..models import get_db
from .. import BOOKS_DIR

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _existing_books() -> list[dict]:
    if not BOOKS_DIR.exists():
        return []
    out = []
    for f in sorted(BOOKS_DIR.glob("*.pdf")):
        out.append({"name": f.name, "size_kb": f.stat().st_size // 1024})
    return out


@router.get("/books")
async def books(request: Request, db: Session = Depends(get_db),
                done: str | None = None, error: str | None = None):
    papers = db.execute(text(
        "SELECT id, year, name, question_count FROM papers "
        "WHERE question_count > 0 ORDER BY year DESC, name")).all()
    tags = db.execute(text(
        "SELECT je.value AS tag, COUNT(*) AS n FROM questions q, "
        "json_each(q.knowledge_tags) je GROUP BY je.value "
        "ORDER BY n DESC")).all()
    return templates.TemplateResponse(request, "books.html", {
        "files": _existing_books(), "papers": papers, "tags": tags,
        "done": done or "", "error": error or "",
    })


@router.post("/books/paper")
async def make_paper_book(paper_id: int, db: Session = Depends(get_db)):
    from bookmaker.book import build_paper_book
    try:
        paths = build_paper_book(db, paper_id)
        return RedirectResponse(f"/books?done={paths[0].name}", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/books?error={e}", status_code=303)


@router.post("/books/topic")
async def make_topic_book(tag: str, db: Session = Depends(get_db)):
    from bookmaker.book import build_topic_book
    try:
        paths = build_topic_book(db, tag)
        return RedirectResponse(f"/books?done={paths[0].name}", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/books?error={e}", status_code=303)


@router.post("/books/custom")
async def make_custom_book(ids: str, title: str = "自选题单",
                           db: Session = Depends(get_db)):
    from bookmaker.book import build_custom_book
    try:
        qids = [int(x) for x in ids.replace("，", ",").split(",")
                if x.strip().isdigit()][:200]
        paths = build_custom_book(db, qids, title)
        return RedirectResponse(f"/books?done={paths[0].name}", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/books?error={e}", status_code=303)


@router.get("/books/download/{name}")
async def download_book(name: str):
    f = (BOOKS_DIR / name).resolve()
    try:
        f.relative_to(BOOKS_DIR.resolve())
    except ValueError:
        raise HTTPException(404)
    if not f.is_file() or f.suffix != ".pdf":
        raise HTTPException(404)
    return FileResponse(f, media_type="application/pdf", filename=f.name)
