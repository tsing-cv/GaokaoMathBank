"""eol 模拟题采集器纯函数测试(静态图片流路线,无需无头浏览器)。"""
from collector.ingesters.eol_mock import (
    meta_from_title, paginated_urls, parse_list_page, parse_paper_page)


def test_parse_list_page_filters_and_extracts():
    html = """
    <div class="fline"><a href="./201804/t20180413_1595191.shtml">2018高考模拟试题及答案（一）：数学（理）</a></div>
    <div class="fline"><a href="./201811/t20181115_1633143.shtml">2018年普通高等学校招生考试浙江卷真题及答案：数学</a></div>
    <div class="fline"><a href="./202104/t20210422_2100462.shtml">2021年广东省高考模拟题：数学</a></div>
    <div class="fline"><a href="./202104/t20210422_2100462.shtml">同链接第二次出现应合并</a></div>
    """
    items = parse_list_page(html)
    urls = [u for u, _ in items]
    assert urls == ["./201804/t20180413_1595191.shtml",
                    "./202104/t20210422_2100462.shtml"]   # 真题过滤+去重保序


def test_parse_list_page_filters_nav_entries():
    """导航链接文案("详细")不是试卷条目,不得入库。"""
    html = """
    <div class="fline"><a href="./201811/t20181115_1633143.shtml">详细</a></div>
    <div class="fline"><a href="./202104/t20210422_2100462.shtml">2021年广东省高考模拟题：数学</a></div>
    """
    items = parse_list_page(html)
    assert items == [("./202104/t20210422_2100462.shtml",
                      "2021年广东省高考模拟题：数学")]


def test_parse_paper_page_images_and_pages():
    html = """
    <p><a><img src="./W020180413419038618487.jpg" /></a></p>
    <img src="https://www.eol.cn/images/ad/2017_img/arrow.png">
    <img src="//img.eol.cn/e_images/gk/2020/newzsgk.jpg">
    <script>var _PAGE_COUNT = "12"; var _PAGE_INDEX = "0";
    var _PAGE_NAME = "t20180413_1595191";</script>
    """
    got = parse_paper_page(html)
    assert got["pages"] == 12
    assert got["images"] == ["./W020180413419038618487.jpg"]  # 只取正文 W0 图


def test_meta_from_title_variants():
    cases = [
        ("2018高考模拟试题及答案（一）：数学（理）",
         {"year": 2018, "province": "通用", "subject": "理科"}),
        ("2021年山东省高考模拟题：数学",
         {"year": 2021, "province": "山东", "subject": "文理同卷"}),
        ("2019年全国高考模拟试卷及答案：数学（文科）",
         {"year": 2019, "province": "全国", "subject": "文科"}),
        ("2019年浙江省第一次联考试题：数学",
         {"year": 2019, "province": "浙江", "subject": "文理同卷"}),
        ("2019江苏高考压轴试题及答案：数学",
         {"year": 2019, "province": "江苏", "subject": "文理同卷"}),
    ]
    for title, expect in cases:
        meta = meta_from_title(title)
        for k, v in expect.items():
            assert meta[k] == v, (title, k, meta[k], v)
        assert meta["exam_type"] == "模拟"
        assert meta["name"] == title


def test_paginated_urls():
    base = "https://gaokao.eol.cn/shiti/gkmn/sxmn/201804/t20180413_1595191.shtml"
    urls = paginated_urls(base, 3)
    assert urls == [
        base,
        "https://gaokao.eol.cn/shiti/gkmn/sxmn/201804/t20180413_1595191_1.shtml",
        "https://gaokao.eol.cn/shiti/gkmn/sxmn/201804/t20180413_1595191_2.shtml",
    ]
