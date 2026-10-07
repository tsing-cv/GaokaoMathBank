"""试卷列表 + 整卷视图 API 测试。"""
import pathlib

from fastapi.testclient import TestClient

from app import models
from app.models import Paper, Question


def _setup(tmp_path):
    models.rebind_db(str(tmp_path / "t.db"))
    from app.main import app
    with models.SessionLocal() as db:
        p1 = Paper(year=2024, province="北京", exam_type="真题", subject="文理同卷",
                   name="2024年北京卷数学", source_name="github-gaokao-latex",
                   source_url="http://x/1", status="parsed", question_count=2)
        p2 = Paper(year=2023, province="上海", exam_type="真题", subject="文理同卷",
                   name="2023年上海卷数学", source_name="github-gaokao-latex",
                   source_url="http://x/2", status="parsed", question_count=1)
        db.add_all([p1, p2]); db.commit(); db.refresh(p1); db.refresh(p2)
        db.add_all([
            Question(paper_id=p1.id, seq=1, qtype="选择",
                     stem=[{"t": "text", "c": "已知集合"},
                           {"t": "latex", "c": "A=\\{1,2\\}"}],
                     options=[{"label": "A", "segs": [{"t": "text", "c": "{1}"}]}],
                     answer=[{"t": "text", "c": "B"}], analysis=[],
                     knowledge_tags=["集合"], source_hash="h1"),
            Question(paper_id=p1.id, seq=2, qtype="解答",
                     stem=[{"t": "text", "c": "求导数"}],
                     options=[], answer=[], analysis=[],
                     knowledge_tags=[], source_hash="h2"),
            Question(paper_id=p2.id, seq=1, qtype="填空",
                     stem=[{"t": "text", "c": "椭圆离心率"}],
                     options=[], answer=[], analysis=[],
                     knowledge_tags=[], source_hash="h3"),
        ])
        db.commit()
    return TestClient(app), p1.id, p2.id


def test_papers_list_and_filter(tmp_path):
    client, p1, p2 = _setup(tmp_path)
    r = client.get("/papers")
    assert r.status_code == 200
    assert "2024年北京卷数学" in r.text
    assert "2023年上海卷数学" in r.text
    # 年份筛选
    r = client.get("/papers", params={"year": 2024})
    assert "2024年北京卷数学" in r.text
    assert "2023年上海卷数学" not in r.text
    # 省份筛选
    r = client.get("/papers", params={"province": "上海"})
    assert "2023年上海卷数学" in r.text
    assert "2024年北京卷数学" not in r.text


def test_papers_pagination(tmp_path):
    client, *_ = _setup(tmp_path)
    r = client.get("/papers", params={"page_size": 1, "page": 1})
    assert r.status_code == 200
    assert "2024年北京卷数学" in r.text      # 年份倒序,第一页是 2024
    assert "2023年上海卷数学" not in r.text
    r2 = client.get("/papers", params={"page_size": 1, "page": 2})
    assert "2023年上海卷数学" in r2.text


def test_paper_detail(tmp_path):
    client, p1, _ = _setup(tmp_path)
    r = client.get(f"/paper/{p1}")
    assert r.status_code == 200
    assert "已知集合" in r.text
    assert "求导数" in r.text
    assert "显示答案" in r.text  # 答案折叠
    r = client.get("/paper/99999")
    assert r.status_code == 404


def test_paper_pdf_guard(tmp_path):
    client, p1, _ = _setup(tmp_path)
    # 无 pdf_path → 404
    r = client.get(f"/paper/{p1}/pdf")
    assert r.status_code == 404
    # 路径越界 → 404(不泄露任意文件)
    with models.SessionLocal() as db:
        db.query(Paper).filter_by(id=p1).update(
            {"pdf_path": str(tmp_path / "outside.pdf")})
        db.commit()
    fake = tmp_path / "outside.pdf"
    fake.write_text("x")
    r = client.get(f"/paper/{p1}/pdf")
    assert r.status_code == 404
    # RAW_DIR 内合法文件 → 200
    from app import RAW_DIR
    safe = RAW_DIR / "test_paper.pdf"
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_bytes(b"%PDF-1.4")
    try:
        with models.SessionLocal() as db:
            db.query(Paper).filter_by(id=p1).update({"pdf_path": str(safe)})
            db.commit()
        r = client.get(f"/paper/{p1}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
    finally:
        safe.unlink(missing_ok=True)


def test_papers_blank_year_param(tmp_path):
    """试卷库筛选表单空 year= 空串不得 422(同 /questions 修复)。"""
    from fastapi.testclient import TestClient
    from app.main import app
    models.rebind_db(str(tmp_path / "t.db"))
    with models.SessionLocal() as db:
        db.add(Paper(year=2024, province="北京", exam_type="真题",
                     subject="文理同卷", name="2024年北京卷",
                     source_name="t", status="parsed", question_count=1))
        db.commit()
    r = TestClient(app).get("/papers", params={"year": "", "province": ""})
    assert r.status_code == 200
    assert "2024年北京卷" in r.text
