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


def test_save_paper_backfills_by_province_subject(tmp_path):
    """name 措辞不一致时,按(年,卷种,文理)二级匹配回填附件。"""
    rebind_db(str(tmp_path / "t.db"))
    with SessionLocal() as db:
        # tex 源 \chapter name 与 PDF 侧构造的 name 差一个字
        p1 = save_paper_payload(db, {
            "year": 2008, "province": "四川延考", "exam_type": "真题",
            "subject": "文科", "name": "2008年四川延考卷（文）",
            "questions": []})
        p2 = save_paper_payload(db, {
            "year": 2008, "province": "四川延考", "exam_type": "真题",
            "subject": "文科", "name": "2008年四川延考（文）",
            "pdf_path": "/raw/y.pdf", "questions": []})
        assert p2.id == p1.id
        assert p2.pdf_path == "/raw/y.pdf"


def test_meta_from_pdf_filename():
    """gaokaomath 文件名归一到库内卷种词表(罗马数字/甲乙卷/新高考)。"""
    from tools.run_collect import meta_from_pdf_filename as mf
    cases = [
        ("2025全国1(山东,广东).pdf",
         {"year": 2025, "province": "全国I卷", "subject": "文理同卷"}),
        ("2024全国文(西藏,四川).pdf",
         {"year": 2024, "province": "全国甲卷", "subject": "文科"}),
        ("2024全国理(西藏,四川).pdf",
         {"year": 2024, "province": "全国甲卷", "subject": "理科"}),
        ("2024新高考1(山东,广东).pdf",
         {"year": 2024, "province": "新高考I卷", "subject": "新高考"}),
        ("2020全国1文(河南,河北).pdf",
         {"year": 2020, "province": "全国I卷", "subject": "文科"}),
        ("2010大纲2理(甘肃,贵州).pdf",
         {"year": 2010, "province": "大纲II卷", "subject": "理科"}),
        ("2010新课标文(海南,宁夏).pdf",
         {"year": 2010, "province": "新课标卷", "subject": "文科"}),
        ("2013新课标1文(河南,河北).pdf",
         {"year": 2013, "province": "新课标I卷", "subject": "文科"}),
        ("2014新课标2理(青海,西藏).pdf",
         {"year": 2014, "province": "新课标II卷", "subject": "理科"}),
        ("2008四川延考文.pdf",
         {"year": 2008, "province": "四川延考", "subject": "文科"}),
        ("2008四川理.pdf",
         {"year": 2008, "province": "四川", "subject": "理科"}),
        ("2021全国乙理(河南,山西).pdf",
         {"year": 2021, "province": "全国乙卷", "subject": "理科"}),
        ("2024北京.pdf",
         {"year": 2024, "province": "北京", "subject": "文理同卷"}),
        ("春季2019上海.pdf",
         {"year": 2019, "province": "上海(春季)", "subject": "文理同卷"}),
        ("2013春季上海.pdf",
         {"year": 2013, "province": "上海(春季)", "subject": "文理同卷"}),
        ("2026上海春季.pdf",
         {"year": 2026, "province": "上海(春季)", "subject": "文理同卷"}),
    ]
    for fname, expect in cases:
        meta = mf(fname)
        for k, v in expect.items():
            assert meta[k] == v, (fname, k, meta[k], v)


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
