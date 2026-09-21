from pipeline.tagger import rule_tag


def test_rule_tag_sequence():
    q = {"stem": [{"t": "text", "c": "已知等差数列前n项和"},
                  {"t": "latex", "c": "S_n"}], "options": [], "answer": [], "analysis": []}
    assert "数列" in rule_tag(q)


def test_rule_tag_geometry():
    q = {"stem": [{"t": "text", "c": "如图,四棱锥的体积为"}],
         "options": [], "answer": [], "analysis": []}
    assert "立体几何" in rule_tag(q)


def test_rule_tag_multi():
    q = {"stem": [{"t": "text", "c": "已知椭圆的离心率,过焦点作直线"}],
         "options": [], "answer": [], "analysis": []}
    tags = rule_tag(q)
    assert "解析几何" in tags


def test_rule_tag_fallback():
    q = {"stem": [{"t": "text", "c": "某数学文化背景题"}],
         "options": [], "answer": [], "analysis": []}
    assert rule_tag(q) == ["待标注"] or "综合" in rule_tag(q)
