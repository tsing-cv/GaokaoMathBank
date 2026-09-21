"""/books 成册页测试(生成走真 weasyprint,缺失时跳过)。"""
import pytest
from fastapi.testclient import TestClient

from app import models
from app.models import Paper, Question

try:
    import weasyprint  # noqa: F401
    HAS_WP = True
except Exception:
    HAS_WP = False


def _setup(tmp_path):
    models.rebind_db(str(tmp_path / "t.db"))
    from app.main import app
    with models.SessionLocal() as db:
        p = Paper(year=2024, province="北京", exam_type="真题",
                  subject="文理同卷", name="2024年北京卷",
                  source_name="github-gaokao-latex",
                  source_url="http://x", status="parsed", question_count=2)
        db.add(p); db.commit(); db.refresh(p)
        db.add_all([
            Question(paper_id=p.id, seq=1, qtype="选择",
                     stem=[{"t": "text", "c": "已知集合"},
                           {"t": "latex", "c": "A=\\{1\\}"}],
                     options=[], answer=[{"t": "text", "c": "A"}],
                     analysis=[{"t": "text", "c": "逐一验证"}],
                     knowledge_tags=["集合与逻辑"], source_hash="b1"),
            Question(paper_id=p.id, seq=2, qtype="解答",
                     stem=[{"t": "text", "c": "求椭圆离心率"}],
                     options=[], answer=[], analysis=[],
                     knowledge_tags=["解析几何"], source_hash="b2"),
        ])
        db.commit()
    return TestClient(app), p.id


def test_books_page_lists_forms(tmp_path):
    client, _ = _setup(tmp_path)
    r = client.get("/books")
    assert r.status_code == 200
    assert "整卷汇编" in r.text
    assert "知识点专题汇编" in r.text
    assert "自选题单" in r.text
    assert "2024年北京卷" in r.text


def test_books_download_guard(tmp_path):
    client, _ = _setup(tmp_path)
    r = client.get("/books/download/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code == 404
    r = client.get("/books/download/nope.pdf")
    assert r.status_code == 404


@pytest.mark.skipif(not HAS_WP, reason="weasyprint 系统依赖未安装")
def test_make_paper_book(tmp_path):
    client, pid = _setup(tmp_path)
    r = client.post("/books/paper", params={"paper_id": pid},
                    follow_redirects=False)
    assert r.status_code == 303
    assert "done=" in r.headers["location"]
    name = r.headers["location"].split("done=")[1]
    dl = client.get(f"/books/download/{name}")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("application/pdf")
    assert dl.content[:5] == b"%PDF-"


@pytest.mark.skipif(not HAS_WP, reason="weasyprint 系统依赖未安装")
def test_make_topic_and_custom(tmp_path):
    client, pid = _setup(tmp_path)
    r = client.post("/books/topic", params={"tag": "解析几何"},
                    follow_redirects=False)
    assert r.status_code == 303 and "done=" in r.headers["location"]
    with models.SessionLocal() as db:
        ids = [q.id for q in db.query(Question).all()]
    r = client.post("/books/custom",
                    params={"ids": ",".join(map(str, ids)), "title": "测试题单"},
                    follow_redirects=False)
    assert r.status_code == 303 and "done=" in r.headers["location"]
