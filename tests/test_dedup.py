from app.models import Question, Paper, rebind_db, SessionLocal
from pipeline.dedup import rebuild_fts, dedup_questions


def _mk(db, h):
    p = db.query(Paper).first()
    if not p:
        p = Paper(year=2024, province="x", exam_type="真题", subject="y",
                  name="z", status="parsed")
        db.add(p); db.commit()
    db.add(Question(paper_id=p.id, seq=1, qtype="填空",
                    stem=[{"t": "text", "c": "同题"}], options=[], answer=[],
                    analysis=[], knowledge_tags=[], source_hash=h))
    db.commit()


def test_dedup_and_fts(tmp_path):
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        _mk(db, "h1"); _mk(db, "h1"); _mk(db, "h2")
        deleted = dedup_questions(db)
        assert deleted == 1
        # FTS 需要虚表(rebind_db 只建了普通表)
        from sqlalchemy import text
        with db.connection().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS questions_fts USING fts5("
                              "question_id UNINDEXED, body, tokenize='trigram')"))
        db.commit()
        assert rebuild_fts(db) == 2
        # 检索验证
        row = db.execute(text(
            "SELECT question_id FROM questions_fts WHERE questions_fts MATCH '同题'")).first()
        assert row is not None
