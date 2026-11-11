# -*- coding: utf-8 -*-
"""题目标注 API 和页面"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Question, get_db
from .common import OptIntQuery
from .questions import _j, _preview_html, _row_items

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates"))

PAGE_SIZE = 20

# 可用知识点标签
AVAILABLE_TAGS = [
    "集合与逻辑", "函数", "三角函数", "数列", "不等式",
    "导数", "向量", "复数", "立体几何", "解析几何",
    "概率统计", "排列组合", "数学文化", "极坐标与参数方程", "平面几何"
]


@router.get("/annotate")
async def annotate_page(request: Request, db: Session = Depends(get_db),
                        page: int = 1, page_size: int = PAGE_SIZE):
    """标注页面：显示待标注的题目"""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)

    # 查询待标注的题目
    cond = " AND q.knowledge_tags = '[\"待标注\"]'"
    total = db.execute(text(f"SELECT COUNT(*) FROM questions q "
                            f"JOIN papers p ON p.id = q.paper_id WHERE 1=1{cond}"),
                       {}).scalar() or 0

    rows = db.execute(text(
        """SELECT q.id, q.seq, q.qtype, q.stem, q.options, q.answer, q.analysis,
                  q.knowledge_tags, p.id AS paper_id, p.year, p.name AS paper_name
           FROM questions q JOIN papers p ON p.id = q.paper_id
           WHERE 1=1""" + cond + """
           ORDER BY p.year DESC, p.name, q.seq
           LIMIT :lim OFFSET :off"""),
        {"lim": page_size, "off": (page - 1) * page_size}).all()

    items = _row_items(rows, None)

    return templates.TemplateResponse(request, "annotate.html", {
        "items": items,
        "total": total,
        "page": page,
        "pages": max(math.ceil(total / page_size), 1),
        "tags": AVAILABLE_TAGS,
        "request": request,
    })


@router.post("/annotate/{qid}")
async def update_tags(request: Request, qid: int,
                      tags: List[str] = [],
                      db: Session = Depends(get_db)):
    """更新题目的知识点标签"""
    q = db.get(Question, qid)
    if not q:
        raise HTTPException(404, detail="题目不存在")

    # 如果没有选择标签，保持待标注
    if not tags:
        q.knowledge_tags = json.dumps(["待标注"], ensure_ascii=False)
    else:
        q.knowledge_tags = json.dumps(tags, ensure_ascii=False)

    db.commit()
    db.refresh(q)

    return {"success": True, "tags": json.loads(q.knowledge_tags)}


@router.get("/api/tags")
async def get_available_tags():
    """获取可用标签列表"""
    return {"tags": AVAILABLE_TAGS}
