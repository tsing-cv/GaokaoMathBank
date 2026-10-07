"""tools/normalize_province:历史库拼音 province → 中文迁移逻辑测试。"""
from app.models import Paper, rebind_db, SessionLocal
from tools.normalize_province import normalize_provinces


def _mk(db, **kw):
    d = dict(year=1977, province="national", exam_type="真题", subject="文理同卷",
             name="1977年全国卷", source_name="github-gaokao-latex",
             source_url="", pdf_path="", status="parsed", question_count=0)
    d.update(kw)
    p = Paper(**d)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_pinyin_to_chinese(tmp_path):
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        p = _mk(db, province="beijing_liberal_autumn", name="2002年北京卷（秋文）")
        stats = normalize_provinces(db)
        assert stats["updated"] == 1
        db.refresh(p)
        assert p.province == "北京"


def test_empty_province_becomes_national(tmp_path):
    """gaokaomath 纯年份附件卷(空 province)归一为全国。"""
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        p = _mk(db, province="", name="1952年卷", source_name="github-gaokaomath",
                pdf_path="/raw/1952.pdf")
        stats = normalize_provinces(db)
        assert stats["updated"] == 1
        db.refresh(p)
        assert p.province == "全国"


def test_subject_fixed_from_name_paren(tmp_path):
    """subject=文理同卷但卷名带（文）/（理）时,顺带修正科别。"""
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        p1 = _mk(db, province="anhui_liberal_spring", name="2004年安徽卷（春文）")
        p2 = _mk(db, province="anhui_science_spring", name="2004年安徽卷（春理）")
        normalize_provinces(db)
        db.refresh(p1)
        db.refresh(p2)
        assert p1.subject == "文科"
        assert p2.subject == "理科"
        assert p1.province == p2.province == "安徽"


def test_chinese_provinces_untouched(tmp_path):
    """已是中文的 province 不动(幂等,二次运行为 0)。"""
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        _mk(db, province="上海", name="2024年上海卷")
        stats = normalize_provinces(db)
        assert stats["updated"] == 0


def test_pinyin_with_inline_modifier(tmp_path):
    """文理标记在中间的拼音 key(表里只录了剥修饰形态)也能转中文。"""
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        p1 = _mk(db, province="jing_hui_liberal_spring",
                 name="2000年京皖卷（春文）")
        p2 = _mk(db, province="jing_meng_wan_science_spring",
                 name="2002年京蒙皖卷（春理）")
        normalize_provinces(db)
        db.refresh(p1)
        db.refresh(p2)
        assert p1.province == "京皖"
        assert p2.province == "京蒙皖"


def test_duplicate_merged_into_paper_with_questions(tmp_path):
    """同年同卷种:无题附件卷并入有题卷(回填 pdf 后删除)。
    首页覆盖表将不再出现 1952 年'全国卷/年卷'两行。"""
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        tex = _mk(db, province="national", name="1952年全国卷",
                  question_count=10)
        extra = _mk(db, province="", name="1952年卷",
                    source_name="github-gaokaomath", pdf_path="/raw/1952.pdf")
        stats = normalize_provinces(db)
        assert stats["merged"] == 1
        db.refresh(tex)
        assert tex.pdf_path == "/raw/1952.pdf"      # 附件回填到有题卷
        assert db.get(Paper, extra.id) is None       # 空卷已删
        assert db.query(Paper).count() == 1


def test_bare_year_paper_kept_when_no_sibling(tmp_path):
    """同年无 tex 卷时,空 province 卷保留(只归一 province/name)。"""
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        p = _mk(db, province="", name="1979年卷", source_name="github-gaokaomath",
                pdf_path="/raw/1979.pdf")
        stats = normalize_provinces(db)
        assert stats["merged"] == 0
        db.refresh(p)
        assert p.province == "全国"
        assert p.name == "1979年全国卷"               # 规范名,重采可一级去重
