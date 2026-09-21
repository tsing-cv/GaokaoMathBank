import pathlib

from collector.ingesters.pdf_archive import parse_paper_text

FIX = pathlib.Path(__file__).parent / "fixtures" / "sample_paper.txt"


def test_parse_sample_paper():
    meta = {"year": 2024, "province": "新高考I卷", "exam_type": "真题",
            "subject": "新高考", "name": "2024年新高考I卷数学"}
    result = parse_paper_text(FIX.read_text(encoding="utf-8"), meta)
    qs = result["questions"]
    assert len(qs) == 5, f"应解析出5题,得到{len(qs)}"
    assert qs[0]["qtype"] == "选择"
    assert qs[0]["options"] and qs[0]["options"][0]["label"] == "A"
    assert qs[2]["seq"] == 13 and qs[2]["qtype"] == "填空"
    assert qs[4]["qtype"] == "解答"
    assert qs[0]["answer"], "参考答案应被关联"
    assert any(s["t"] == "latex" for s in qs[0]["stem"])


def test_watermark_and_nav_noise_removed():
    meta = {"year": 2024, "province": "北京", "exam_type": "真题",
            "subject": "理科", "name": "x"}
    noisy = ("广告位招租 QQ:123456\n"
             "1. 求值 $1+1$\n"
             "来源:某网站 www.x.com\n"
             "2. 求 $2+2$\n"
             "参考答案\n"
             "1.$2$ 2.$4$")
    result = parse_paper_text(noisy, meta)
    joined = "".join(s["c"] for q in result["questions"] for s in q["stem"])
    assert "广告" not in joined and "www.x.com" not in joined
    assert len(result["questions"]) == 2
