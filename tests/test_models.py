from app.models import Paper, Question, Asset
from app import models


def test_create_paper_and_question(tmp_path):
    # 用独立临时库,避免污染开发库
    models.rebind_db(str(tmp_path / "t.db"))
    with models.SessionLocal() as db:
        p = Paper(year=2024, province="新高考I卷", exam_type="真题",
                  subject="新高考", name="2024年新高考I卷数学",
                  source_name="测试", status="parsed")
        db.add(p); db.commit(); db.refresh(p)
        q = Question(paper_id=p.id, seq=1, qtype="选择",
                     stem=[{"t": "text", "c": "题干"}],
                     answer=[{"t": "text", "c": "A"}], analysis=[],
                     knowledge_tags=["集合"], source_hash="abc123")
        db.add(q); db.commit(); db.refresh(q)
        assert q.id and q.paper_id == p.id
        a = Asset(question_id=q.id, local_path="/assets/x.png", kind="figure")
        db.add(a); db.commit()
        assert db.query(Asset).filter(Asset.question_id == q.id).count() == 1
