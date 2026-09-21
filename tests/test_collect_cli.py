from app.models import Question, rebind_db, SessionLocal
from tools.run_collect import save_paper_payload, meta_from_tex_filename


def test_save_paper_dedup(tmp_path):
    rebind_db(str(tmp_path / "t.db"))
    payload = {"year": 2024, "province": "新高考I卷", "exam_type": "真题",
               "subject": "新高考", "name": "2024年新高考I卷",
               "questions": [{"seq": 1, "qtype": "选择",
                              "stem": [{"t": "text", "c": "题干"}],
                              "options": [], "answer": [], "analysis": []}]}
    with SessionLocal() as db:
        p1 = save_paper_payload(db, payload)
        p2 = save_paper_payload(db, payload)  # 重复导入 → 同一卷
        assert p1.id == p2.id
        assert db.query(Question).count() == 1


def test_save_paper_backfills_pdf(tmp_path):
    """附件源(PDF)登记已存在的卷时回填 pdf_path,不新建重复卷。"""
    rebind_db(str(tmp_path / "t.db"))
    payload = {"year": 2010, "province": "北京", "exam_type": "真题",
               "subject": "理科", "name": "2010年北京卷（理）",
               "questions": [{"seq": 1, "qtype": "选择",
                              "stem": [{"t": "text", "c": "题干"}],
                              "options": [], "answer": [], "analysis": []}]}
    with SessionLocal() as db:
        p1 = save_paper_payload(db, payload)
        assert p1.pdf_path == ""
        p2 = save_paper_payload(db, {**payload, "pdf_path": "/raw/x.pdf",
                                     "questions": []})
        assert p2.id == p1.id
        assert p2.pdf_path == "/raw/x.pdf"


def test_meta_from_tex_filename():
    cases = [
        ("2024", "new_gaokao_paper_1.tex",
         {"province": "新高考I卷", "subject": "新高考"}),
        ("2024", "national_paper_a_science.tex",
         {"province": "全国甲卷", "subject": "理科"}),
        ("2024", "national_paper_a_liberal.tex",
         {"province": "全国甲卷", "subject": "文科"}),
        ("2006", "anhui_science.tex", {"province": "安徽", "subject": "理科"}),
        ("2006", "jiangsu.tex", {"province": "江苏", "subject": "文理同卷"}),
        ("2010", "new_curriculum_liberal.tex",
         {"province": "新课标卷", "subject": "文科"}),
        ("2024", "shanghai_spring.tex",
         {"province": "上海(春季)", "subject": "文理同卷"}),
        ("2015", "national_paper_2_science.tex",
         {"province": "全国II卷", "subject": "理科"}),
        ("2010", "syllabus_paper_1_science.tex",
         {"province": "大纲I卷", "subject": "理科"}),
        ("2011", "syllabus_liberal.tex", {"province": "大纲卷", "subject": "文科"}),
        ("2014", "new_curriculum_paper_2_science.tex",
         {"province": "新课标II卷", "subject": "理科"}),
        ("2008", "sichuan_postponed_liberal.tex",
         {"province": "四川延考", "subject": "文科"}),
        ("2008", "sichuan_ordinary_science.tex",
         {"province": "四川", "subject": "理科"}),
    ]
    for year, fname, expect in cases:
        meta = meta_from_tex_filename(int(year), fname)
        assert meta["province"] == expect["province"], fname
        assert meta["subject"] == expect["subject"], fname
        assert meta["exam_type"] == "真题"
        assert meta["year"] == int(year)
