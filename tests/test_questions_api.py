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


def test_questions_html_escape(tmp_path):
    """题干含不等号(<)时必须转义,否则裸 < 被浏览器当标签吞掉页面。"""
    client, ids, pid = _setup(tmp_path)
    from pipeline.dedup import rebuild_fts
    with models.SessionLocal() as db:
        db.add(Question(paper_id=pid, seq=9, qtype="填空",
                        stem=[{"t": "text", "c": "当x<0时,求f(x)取值范围"}],
                        options=[], answer=[], analysis=[],
                        knowledge_tags=[], source_hash="k9"))
        db.commit()
        rebuild_fts(db)
    r = client.get("/questions", params={"q": "取值范围"})
    assert r.status_code == 200
    assert "x&lt;0" in r.text
    assert "x<0" not in r.text


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


def test_list_preview_math_delimited(tmp_path):
    """列表预览:latex 段带 $..$ 定界供 KaTeX 渲染——不再剥定界符导致
    公式源码裸奔(用户截图:检索列表显示 \\lg^{2}5 等源码)。"""
    client, ids, _ = _setup(tmp_path)
    r = client.get("/questions", params={"q": "离心率"})
    assert r.status_code == 200
    assert "$\\frac{1}{2}$" in r.text


def test_related_preview_math_delimited(tmp_path):
    """详情页相关题预览:公式同样带 $ 定界渲染,而非源码文本。"""
    client, ids, pid = _setup(tmp_path)
    from pipeline.dedup import rebuild_fts
    with models.SessionLocal() as db:
        q = Question(paper_id=pid, seq=10, qtype="解答",
                     stem=[{"t": "text", "c": "已知数列"},
                           {"t": "latex", "c": "a_n=n^2+1"}],
                     options=[], answer=[], analysis=[],
                     knowledge_tags=["数列"], source_hash="k10")
        db.add(q); db.commit(); db.refresh(q)
        qid = q.id
        rebuild_fts(db)
    # seq=2 数列题详情页:related 区块应含新题且公式带定界
    r = client.get(f"/question/{ids[1]}")
    assert r.status_code == 200
    assert "$a_n=n^2+1$" in r.text


def test_preview_html_keeps_mark_out_of_math():
    """关键词高亮只注入 text 段:<mark> 落进 $..$ 内会撕碎公式。"""
    from app.api.questions import _preview_html
    segs = [{"t": "text", "c": "已知数列"},
            {"t": "latex", "c": "a_{n}"},
            {"t": "text", "c": "的前n项和"}]
    h = _preview_html(segs, "数列")
    assert "已知<mark>数列</mark>" in h
    assert "$a_{n}$" in h
    assert h.count("<mark>") == 1
    # latex 段含 < 时转义(浏览器不吞后续内容)
    h2 = _preview_html([{"t": "latex", "c": "x<0"}], None)
    assert h2 == "$x&lt;0$"


def test_questions_blank_query_params(tmp_path):
    """表单空值(select 未选)提交 year= 空串不得 422:
    2026-09-22 实测 /questions?q=导数&year= 返回 int_parsing 错误。"""
    client, ids, _ = _setup(tmp_path)
    r = client.get("/questions", params={"q": "数列", "year": ""})
    assert r.status_code == 200
    assert "等差" in r.text
    # 正常年份过滤不受影响
    r = client.get("/questions", params={"q": "数列", "year": "2024"})
    assert r.status_code == 200
    assert "等差" in r.text
