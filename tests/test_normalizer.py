from pipeline.normalizer import normalize_question, standardize_latex


def test_latex_delimiters_unified():
    # \(...\) 与【】均统一为 $...$
    assert standardize_latex(r"已知 \(x^2\),且【y_1】") == r"已知 $x^2$,且$y_1$"


def test_unicode_pseudo_formula_kept_as_text():
    # Unicode 伪公式(²、√)不强转,保留文本
    s = standardize_latex("求 x²+1 的值")
    assert "x²" in s


def test_full_width_punct_normalized():
    q = {"stem": [{"t": "text", "c": "已知函数f(x).求导数"}], "options": [],
         "answer": [], "analysis": [{"t": "text", "c": "由题意得."}]}
    nq = normalize_question(q)
    assert nq["stem"][0]["c"] == "已知函数f(x)。求导数"
    assert nq["analysis"][0]["c"] == "由题意得。"


def test_watermark_stripped_in_stem():
    q = {"stem": [{"t": "text", "c": "题干内容 来源:XX网"}], "options": [],
         "answer": [], "analysis": []}
    nq = normalize_question(q)
    assert "来源" not in nq["stem"][0]["c"]
