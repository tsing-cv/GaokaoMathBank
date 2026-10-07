from app.models import Paper, Question, rebind_db, SessionLocal
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


def test_save_paper_image_questions_custom_hash(tmp_path):
    """图片流题(eol 模拟卷):stem 全是 [图],默认 q_hash 会互相冲突,
    payload 显式带 source_hash(图片 URL 指纹)时应被采用。"""
    rebind_db(str(tmp_path / "t.db"))
    payload = {"year": 2021, "province": "山东", "exam_type": "模拟",
               "subject": "文理同卷", "name": "2021年山东省高考模拟题：数学",
               "questions": [
                   {"seq": 1, "qtype": "图片",
                    "stem": [{"t": "img", "c": "/assets/eol/a.jpg"}],
                    "options": [], "answer": [], "analysis": [],
                    "source_hash": "img-a"},
                   {"seq": 2, "qtype": "图片",
                    "stem": [{"t": "img", "c": "/assets/eol/b.jpg"}],
                    "options": [], "answer": [], "analysis": [],
                    "source_hash": "img-b"},
               ]}
    with SessionLocal() as db:
        p1 = save_paper_payload(db, payload)
        assert p1.question_count == 2          # 两图两题,不被误去重
        p2 = save_paper_payload(db, payload)   # 重采同卷 → 卷级命中,题不变
        assert p2.id == p1.id
        assert db.query(Question).count() == 2


def test_save_paper_no_secondary_match_with_questions(tmp_path):
    """模拟题同年同省同科别多套卷:带题 payload 禁用二级匹配,
    否则后续卷被吸进第一套、题目被丢(2026-09-22 eol 实测:
    2018通用(一)~(十五) 仅首套入库,其余全被吞)。"""
    rebind_db(str(tmp_path / "t.db"))
    base = {"year": 2018, "province": "通用", "exam_type": "模拟",
            "subject": "文理同卷"}
    with SessionLocal() as db:
        p1 = save_paper_payload(db, {**base,
            "name": "2018高考模拟试题及答案（十二）：数学",
            "questions": [{"seq": 1, "qtype": "图片",
                           "stem": [{"t": "img", "c": "/assets/eol/a.jpg"}],
                           "options": [], "answer": [], "analysis": [],
                           "source_hash": "a"}]})
        p2 = save_paper_payload(db, {**base,
            "name": "2018高考模拟试题及答案（十一）：数学",
            "questions": [{"seq": 1, "qtype": "图片",
                           "stem": [{"t": "img", "c": "/assets/eol/b.jpg"}],
                           "options": [], "answer": [], "analysis": [],
                           "source_hash": "b"}]})
        assert p2.id != p1.id                  # 同 key 不同套 → 各自成卷
        assert p2.question_count == 1          # 题目不被丢弃
        assert db.query(Paper).count() == 2
        assert db.query(Question).count() == 2


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


def test_meta_from_tex_filename_pinyin_variants():
    """带 春/秋/联考/地市 复合修饰的文件名不再拼音裸奔入库
    (2026-09 首页覆盖表暴露 56 个拼音 province 的根因)。"""
    cases = [
        # (年, 文件名, province, subject) —— 数据库实际出现过的 key 抽样
        ("1952", "national.tex", "全国", "文理同卷"),
        ("2004", "national_paper_4_liberal.tex", "全国IV卷", "文科"),
        ("2002", "beijing_liberal_autumn.tex", "北京", "文科"),
        ("2005", "beijing_science_spring.tex", "北京", "理科"),
        ("2004", "anhui_science_spring.tex", "安徽", "理科"),
        ("1993", "jing_xiang_e_yun_qiong_gui_liberal.tex", "京湘鄂云琼贵", "文科"),
        ("2001", "jing_meng_wan_science_spring.tex", "京蒙皖", "理科"),
        ("1958", "hei_ji_liao.tex", "黑吉辽", "文理同卷"),
        ("1958", "hu_min.tex", "沪闽", "文理同卷"),
        ("2001", "henan_guangdong.tex", "豫粤", "文理同卷"),
        ("1977", "jiangsu_nanjing_city.tex", "江苏", "文理同卷"),
        ("1977", "jiangsu_state_farm_system.tex", "江苏", "文理同卷"),
        ("1977", "guangxi_baise_science.tex", "广西", "理科"),
        ("1977", "heilongjiang_preliminary.tex", "黑龙江", "文理同卷"),
        ("1991", "sannan.tex", "三南", "文理同卷"),
        ("1958", "unknown.tex", "其他", "文理同卷"),
        # 原有常规形态不受影响
        ("2006", "anhui_science.tex", "安徽", "理科"),
        ("2024", "national_paper_a_science.tex", "全国甲卷", "理科"),
    ]
    for year, fname, prov, subj in cases:
        meta = meta_from_tex_filename(int(year), fname)
        assert meta["province"] == prov, (fname, meta["province"])
        assert meta["subject"] == subj, (fname, meta["subject"])


def test_meta_from_pdf_filename_bare_year():
    """纯年份文件名(1952.pdf)不再产生空 province,归一为全国卷。"""
    from tools.run_collect import meta_from_pdf_filename as mf
    meta = mf("1952.pdf")
    assert meta["year"] == 1952
    assert meta["province"] == "全国"
    assert meta["name"] == "1952年全国卷"


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
