"""首页(/)覆盖区块测试:按年份聚合 + 卷名可点(2026-09 体验重构)。"""
from fastapi.testclient import TestClient

from app import models
from app.models import Paper, Question


def _setup(tmp_path, extra_papers=()):
    models.rebind_db(str(tmp_path / "t.db"))
    from app.main import app
    with models.SessionLocal() as db:
        papers = [
            Paper(year=2024, province="新高考I卷", exam_type="真题",
                  subject="新高考", name="2024年新高考I卷",
                  source_name="github-gaokao-latex", source_url="",
                  status="parsed", question_count=19),
            Paper(year=2023, province="上海", exam_type="真题",
                  subject="文理同卷", name="2023年上海卷",
                  source_name="github-gaokao-latex", source_url="",
                  status="parsed", question_count=21),
        ]
        papers.extend(extra_papers)
        db.add_all(papers)
        db.commit()
        ids = [p.id for p in papers]
        db.add_all([
            Question(paper_id=ids[0], seq=1, qtype="选择",
                     stem=[{"t": "text", "c": "x"}], options=[], answer=[],
                     analysis=[], knowledge_tags=[], source_hash="d1"),
        ])
        db.commit()
    return TestClient(app)


def test_index_shows_year_links_and_paper_chips(tmp_path):
    """覆盖区块:年份行链到 /papers?year=,每卷 chip 直达 /paper/{id}。"""
    client = _setup(tmp_path)
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert 'href="/papers?year=2024"' in html          # 年份可点
    assert 'href="/paper/' in html                     # 卷 chip 可点
    assert "2024年新高考I卷" in html                    # 中文卷名


def test_index_aggregates_per_year(tmp_path):
    """同年多卷聚成一行:显示卷数与题数合计。"""
    from app.models import Paper as P
    extra = [P(year=2024, province="北京", exam_type="真题", subject="理科",
               name="2024年北京卷", source_name="x", source_url="",
               status="parsed", question_count=20)]
    client = _setup(tmp_path, extra_papers=extra)
    html = client.get("/").text
    # 2024 行:2 卷 39 题(19+20);页面显示两卷 chip
    assert "2 卷" in html
    assert "2024年北京卷" in html


def test_index_caps_chips_per_year(tmp_path):
    """单年卷数过多(1977 年 79 卷)时截断显示,链接去年份筛选页。"""
    from app.models import Paper as P
    extra = [P(year=1977, province=f"p{i}", exam_type="真题",
               subject="文理同卷", name=f"1977年某地卷{i}",
               source_name="x", source_url="", status="parsed",
               question_count=1) for i in range(20)]
    client = _setup(tmp_path, extra_papers=extra)
    html = client.get("/").text
    assert "1977年某地卷19" not in html               # 第 9 个以后不显示
    assert "等20卷" in html                           # 溢出提示
    assert 'href="/papers?year=1977"' in html         # 溢出仍可进入


def test_index_has_no_pinyin_province_column(tmp_path):
    """覆盖区块不再输出省份矩阵表头(拼音列根除)。"""
    from app.models import Paper as P
    extra = [P(year=1958, province="hu_min", exam_type="真题",
               subject="文理同卷", name="1958年沪闽卷",
               source_name="x", source_url="", status="parsed",
               question_count=5)]
    client = _setup(tmp_path, extra_papers=extra)
    html = client.get("/").text
    assert "hu_min" not in html                       # 拼音不落页面
    assert "<th>hu_min</th>" not in html
    assert "1958年沪闽卷" in html                     # 卷名照常显示
