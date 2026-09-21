import pathlib

from collector.ingesters.latex_archive import parse_tex

FIX = pathlib.Path(__file__).parent / "fixtures" / "ng1_2024_sample.tex"


def test_parse_real_2024_ng1():
    """用真实 2024 新高考I卷 LaTeX 源解析。"""
    meta = {"year": 2024, "province": "新高考I卷", "exam_type": "真题",
            "subject": "新高考", "name": "2024年新高考I卷数学"}
    result = parse_tex(FIX.read_text(encoding="utf-8"), meta)
    qs = result["questions"]
    assert len(qs) == 19, f"新高考I卷应19题,得到{len(qs)}"
    # 第1题:选择,4个选项,答案A,含解析
    q1 = qs[0]
    assert q1["seq"] == 1 and q1["qtype"] == "选择"
    assert len(q1["options"]) == 4
    assert q1["options"][0]["label"] == "A"
    # 选项内容含 LaTeX 集合
    assert any(s["t"] == "latex" for s in q1["options"][0]["segs"])
    assert q1["answer"] and q1["answer"][0]["c"] == "A"
    assert q1["analysis"], "解析应被解析"
    # 题干含 latex 段
    assert any(s["t"] == "latex" for s in q1["stem"])
    # 题型分布:8单选+3多选+3填空+5解答
    from collections import Counter
    types = Counter(q["qtype"] for q in qs)
    assert types["选择"] == 11 and types["填空"] == 3 and types["解答"] == 5
    # 解答题(15题+)无选项
    assert qs[14]["qtype"] == "解答" and not qs[14]["options"]


def test_parse_minimal_tex():
    """无section的最小样本:靠choices推断题型。"""
    tex = r"""
\chapter{某年某卷}

\begin{problem}
求值 \(1+1\)
\end{problem}
\begin{answer}
$2$
\end{answer}
\begin{solution}
显然 \(1+1=2\).
\end{solution}
"""
    result = parse_tex(tex, {"year": 2020, "province": "x", "exam_type": "真题",
                             "subject": "y", "name": "z"})
    qs = result["questions"]
    assert len(qs) == 1
    assert qs[0]["qtype"] == "解答"
    assert any(s["t"] == "latex" and "1+1" in s["c"] for s in qs[0]["stem"])
    assert qs[0]["answer"]


def test_braces_in_options():
    r"""选项内含集合大括号(\{转义)不被误切。"""
    tex = r"""
\begin{problem}
已知集合 \(A=\{1,2\}\),则 \(A\cup B\)（\quad）
\choices
    {\(\{1,2\}\)}
    {\(\{1\}\)}
    {\(\{2\}\)}
    {\(\varnothing\)}
\end{problem}
\begin{answer}
A
\end{answer}
"""
    result = parse_tex(tex, {"year": 2020, "province": "x", "exam_type": "真题",
                             "subject": "y", "name": "z"})
    opts = result["questions"][0]["options"]
    assert len(opts) == 4
    from app.segments import segments_to_text
    assert "1,2" in segments_to_text(opts[0]["segs"])
