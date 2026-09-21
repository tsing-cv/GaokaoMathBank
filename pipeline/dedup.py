"""去重与 FTS 回填。

用法:python -m pipeline.dedup
"""
from sqlalchemy import text

from app.models import Question, SessionLocal
from app.segments import segments_to_text


def ensure_fts(db) -> None:
    """确保 FTS 虚表存在(rebind 到新库后可重复调用)。"""
    db.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS questions_fts USING fts5("
                    "question_id UNINDEXED, body, tokenize='trigram')"))
    db.commit()


def dedup_questions(db) -> int:
    """按 source_hash 删除重复题(保留最早),返回删除数。"""
    seen: set[str] = set()
    del_ids: list[int] = []
    for q in db.query(Question).order_by(Question.id).all():
        if q.source_hash in seen:
            del_ids.append(q.id)
        else:
            seen.add(q.source_hash)
    for i in del_ids:
        db.query(Question).filter(Question.id == i).delete()
    db.commit()
    return len(del_ids)


def rebuild_fts(db) -> int:
    """全量回填 questions_fts,返回行数。"""
    ensure_fts(db)
    db.execute(text("DELETE FROM questions_fts"))
    n = 0
    for q in db.query(Question).all():
        body = " ".join(filter(None, [
            segments_to_text(q.stem or []),
            segments_to_text(q.answer or []),
            segments_to_text(q.analysis or []),
            " ".join(q.knowledge_tags or []),
        ]))
        db.execute(text("INSERT INTO questions_fts(question_id, body) VALUES (:i, :b)"),
                   {"i": q.id, "b": body})
        n += 1
    db.commit()
    return n


if __name__ == "__main__":
    with SessionLocal() as db:
        print(f"去重删除 {dedup_questions(db)} 题;FTS 回填 {rebuild_fts(db)} 题")
