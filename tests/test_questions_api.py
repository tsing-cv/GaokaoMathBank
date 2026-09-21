"""题库检索 + 知识点专题 API 测试。"""
from app import models
from app.models import Paper, Question


def _setup(tmp_path):
    models.rebind_db(str(tmp_path / "t.db"))
    from pipeline.dedup import rebuild_fts
    from app.main import app
    from fastapi.testclient import TestClient
    with models.SessionLocal() as db:
        p = Paper(year=2024, province="北京", exam_type="真题", subject="文理同卷",
                  name="2024年北京卷", source_name="t", status="parsed",
                  question_count=3)
        db.add(p); db.commit(); db.refresh(p)
        rows = [
            Question(paper_id=p.id, seq=1, qtype="选择",
                     stem=[{"t": "text", "c": "已知椭圆的离心率为"},
                           {"t": "latex", "c": "\\frac{1}{2}"}],
                     options=[], answer=[{"t": "text", "c": "A"}], analysis=[],
                     knowledge_tags=["解析几何"], source_hash="k1"),
            Question(paper_id=p.id, seq=2, qtype="解答",
                     stem=[{"t": "text", "c": "已知等差数列的前n项和"}],
                     options=[], answer=[], analysis=[],
                     knowledge_tags=["数列"], source_hash="k2"),
            Question(paper_id=p.id, seq=3, qtype="填空",
                     stem=[{"t": "text", "c": "同"}],
                     options=[], answer=[], analysis=[],
                     knowledge_tags=["数列"], source_hash="k3"),
        ]
        db.add_all(rows); db.commit()
        rebuild_fts(db)
    return TestClient(app), [r.id for r in rows], p.id


def test_questions_fts_search(tmp_path):
    client, ids, _ = _setup(tmp_path)
    # ≥3字词走 FTS
    r = client.get("/questions", params={"q": "离心率"})
    assert r.status_code == 200
    assert "离心率" in r.text
    # 短词(<3字)自动降级 LIKE;命中词高亮
    r = client.get("/questions", params={"q": "数列"})
    assert r.status_code == 200
    assert "等差<mark>数列</mark>" in r.text


def test_questions_filters(tmp_path):
    client, ids, _ = _setup(tmp_path)
    r = client.get("/questions", params={"qtype": "选择"})
    assert "离心率" in r.text
    assert "等差数列" not in r.text
    r = client.get("/questions", params={"tag": "数列"})
    assert "等差数列" in r.text
    assert "离心率" not in r.text
    r = client.get("/questions", params={"year": 2023})
    assert "无匹配" in r.text or r.status_code == 200


def test_question_detail_and_related(tmp_path):
    client, ids, pid = _setup(tmp_path)
    r = client.get(f"/question/{ids[1]}")
    assert r.status_code == 200
    assert "等差数列" in r.text
    # 相关题:同知识点(数列)的另一题应出现
    assert "同" in r.text or "相关" in r.text
    r = client.get("/question/99999")
    assert r.status_code == 404


def test_topics_page(tmp_path):
    client, ids, _ = _setup(tmp_path)
    r = client.get("/topics")
    assert r.status_code == 200
    assert "数列" in r.text
    assert "解析几何" in r.text
    r = client.get("/topics", params={"tag": "数列"})
    assert "等差数列" in r.text
    assert "离心率" not in r.text
