from app.models import Question, Paper, rebind_db, SessionLocal
from pipeline.dedup import ensure_fts, rebuild_fts, dedup_questions


def _mk(db, h):
    p = db.query(Paper).first()
    if not p:
        p = Paper(year=2024, province="x", exam_type="真题", subject="y",
                  name="z", status="parsed")
        db.add(p); db.commit()
    db.add(Question(paper_id=p.id, seq=1, qtype="填空",
                    stem=[{"t": "text", "c": "解析几何离心率"}], options=[], answer=[],
                    analysis=[], knowledge_tags=[], source_hash=h))
    db.commit()


def test_dedup_and_fts(tmp_path):
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        ensure_fts(db)
        _mk(db, "h1"); _mk(db, "h1"); _mk(db, "h2")
        deleted = dedup_questions(db)
        assert deleted == 1
        assert rebuild_fts(db) == 2
        # 中文 trigram 检索验证
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT question_id FROM questions_fts WHERE questions_fts MATCH '离心率'")).first()
        assert row is not None
