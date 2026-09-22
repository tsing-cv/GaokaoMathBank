"""题库:/questions FTS检索(LIKE兜底) + /question/{id} 详情 + /topics 专题。"""
import json
import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Question, get_db
from ..segments import segments_to_text


def _j(v):
    """raw SQL 取出的 JSON 列是文本,统一反序列化。"""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return []
    return v or []

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates"))

PAGE_SIZE = 20

# 列表行:题 + 所属卷信息
_ROW_SQL = """
SELECT q.id, q.seq, q.qtype, q.stem, q.options, q.answer, q.analysis,
       q.knowledge_tags, p.id AS paper_id, p.year, p.name AS paper_name
FROM questions q JOIN papers p ON p.id = q.paper_id
"""


def _search_condition(q: str | None) -> tuple[str, dict]:
    """检索条件:≥3字走 FTS trigram,短词降级 LIKE(均在 fts 表 body 上)。"""
    if not q:
        return "", {}
    kw = q.replace('"', "").strip()
    if not kw:
        return "", {}
    if len(kw) >= 3:
        return (" AND q.id IN (SELECT question_id FROM questions_fts "
                "WHERE questions_fts MATCH :fts_q)"), {"fts_q": f'"{kw}"'}
    return (" AND q.id IN (SELECT question_id FROM questions_fts "
            "WHERE body LIKE :like_q)"), {"like_q": f"%{kw}%"}


def _highlight(plain: str, kw: str | None) -> str:
    """先整体 HTML 转义再做关键词高亮(模板以 |safe 输出)。

    题干常含不等号(x<0),裸 < 会被浏览器当标签开头吞掉后续内容,
    整个结果列表破版——这是"检索页没法用"的根因。
    """
    import html as _html
    plain = _html.escape(plain)
    if kw:
        k = _html.escape(kw.strip())
        if k and k in plain:
            plain = plain.replace(k, f"<mark>{k}</mark>")
    return plain


def _row_items(rows, kw: str | None) -> list[dict]:
    return [{"id": r.id, "seq": r.seq, "qtype": r.qtype,
             "plain": _highlight(segments_to_text(_j(r.stem))[:160], kw),
             "has_answer": bool(_j(r.answer)),
             "has_analysis": bool(_j(r.analysis)),
             "tags": _j(r.knowledge_tags), "paper_id": r.paper_id,
             "year": r.year, "paper_name": r.paper_name}
            for r in rows]


@router.get("/questions")
async def questions(request: Request, db: Session = Depends(get_db),
                    q: str | None = None, qtype: str | None = None,
                    tag: str | None = None, year: int | None = None,
                    page: int = 1, page_size: int = PAGE_SIZE):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    cond, params = _search_condition(q)
    p = dict(params)
    if qtype:
        cond += " AND q.qtype = :qtype"
        p["qtype"] = qtype
    if tag:
        cond += (" AND EXISTS (SELECT 1 FROM json_each(q.knowledge_tags) je "
                 "WHERE je.value = :tag)")
        p["tag"] = tag
    if year:
        cond += " AND p.year = :year"
        p["year"] = year
    total = db.execute(text(f"SELECT COUNT(*) FROM questions q "
                            f"JOIN papers p ON p.id = q.paper_id WHERE 1=1{cond}"),
                       p).scalar() or 0
    rows = db.execute(text(
        _ROW_SQL + f" WHERE 1=1{cond} ORDER BY p.year DESC, p.name, q.seq "
        f"LIMIT :lim OFFSET :off"),
        {**p, "lim": page_size, "off": (page - 1) * page_size}).all()
    years = [r[0] for r in db.execute(
        text("SELECT DISTINCT year FROM papers ORDER BY year DESC"))]
    return templates.TemplateResponse(request, "questions.html", {
        "items": _row_items(rows, q), "total": total, "page": page,
        "pages": max(math.ceil(total / page_size), 1),
        "years": years, "cur": {"q": q or "", "qtype": qtype or "",
                                "tag": tag or "", "year": year or ""},
    })


@router.get("/question/{qid}")
async def question_detail(request: Request, qid: int,
                          db: Session = Depends(get_db)):
    q = db.get(Question, qid)
    if not q:
        raise HTTPException(404)
    row = db.execute(text(
        "SELECT id, year, name FROM papers WHERE id = :pid"),
        {"pid": q.paper_id}).first()
    # 相关题:共享任一知识点,排除自身
    related = db.execute(text(
        "SELECT DISTINCT q2.id, q2.stem, p.year, p.name FROM questions q2, "
        "questions q, papers p WHERE p.id = q2.paper_id AND q.id = :qid "
        "AND q2.id != q.id AND EXISTS ("
        "  SELECT 1 FROM json_each(q2.knowledge_tags) t2 "
        "  JOIN json_each(q.knowledge_tags) t1 ON t1.value = t2.value) "
        "LIMIT 5"), {"qid": qid}).all()
    return templates.TemplateResponse(request, "question_detail.html", {
        "q": q, "paper": row,
        "related": [{"id": r.id, "plain": segments_to_text(_j(r.stem))[:100],
                     "year": r.year, "name": r.name} for r in related],
    })


@router.get("/topics")
async def topics(request: Request, db: Session = Depends(get_db),
                 tag: str | None = None, page: int = 1,
                 page_size: int = PAGE_SIZE):
    """知识点专题:无 tag 出计数总览,有 tag 出该标签题目。"""
    if not tag:
        rows = db.execute(text(
            "SELECT je.value AS tag, COUNT(*) AS n FROM questions q, "
            "json_each(q.knowledge_tags) je GROUP BY je.value "
            "ORDER BY n DESC")).all()
        return templates.TemplateResponse(request, "topics.html", {
            "overview": True, "counts": rows})
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)
    cond = (" AND EXISTS (SELECT 1 FROM json_each(q.knowledge_tags) je "
            "WHERE je.value = :tag)")
    total = db.execute(text(f"SELECT COUNT(*) FROM questions q JOIN papers p "
                            f"ON p.id = q.paper_id WHERE 1=1{cond}"),
                       {"tag": tag}).scalar() or 0
    rows = db.execute(text(
        _ROW_SQL + f" WHERE 1=1{cond} ORDER BY p.year DESC, p.name, q.seq "
        f"LIMIT :lim OFFSET :off"),
        {"tag": tag, "lim": page_size, "off": (page - 1) * page_size}).all()
    return templates.TemplateResponse(request, "topics.html", {
        "overview": False, "tag": tag, "items": _row_items(rows, None),
        "total": total, "page": page,
        "pages": max(math.ceil(total / page_size), 1)})
