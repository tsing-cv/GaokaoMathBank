"""reparse:字段级结构修复——text 段残留环境/命令的转换。"""
from pipeline.reparse import repair_fields


def _mp(p):
    return "/assets/" + p if "/" in p else None


def test_circlelist_items_numbered():
    segs = [{"t": "text", "c": "结论： \\begin{circlelist} \\item 若"},
            {"t": "latex", "c": "\\{a_n\\}"},
            {"t": "text", "c": "等差，则 M 有 1 个； \\item 等比，"},
            {"t": "text", "c": "则 2 个. \\end{circlelist} 序号是\\fillinblank{}。"}]
    out, _ = repair_fields(segs, _mp)
    flat = "".join(s["c"] for s in out if s["t"] == "text")
    assert "circlelist" not in flat
    assert "①" in flat and "②" in flat      # \item 序号化,跨段连续
    assert "fillinblank" not in flat and "____" in flat  # text 语境填空线


def test_enumerate_numbered():
    segs = [{"t": "text", "c": "\\begin{enumerate} \\item 求 a; \\item 求 b. \\end{enumerate}"}]
    out, _ = repair_fields(segs, _mp)
    flat = "".join(s["c"] for s in out if s["t"] == "text")
    assert "(1)" in flat and "(2)" in flat


def test_image_commands_variants():
    segs = [{"t": "text",
             "c": "如图 \\texfigure[max width=0.78\\linewidth]{img/2024/a/f.png} "
                  "又见 \\solutionfigure{img_repaint/2006/b.png} "
                  "声明 \\FigureLayoutDeclare{img/2024/c.png}"}]
    out, _ = repair_fields(segs, _mp)
    imgs = [s for s in out if s["t"] == "img"]
    assert [s["c"] for s in imgs] == ["/assets/img/2024/a/f.png",
                                      "/assets/img_repaint/2006/b.png",
                                      "/assets/img/2024/c.png"]
    assert all("texfigure" not in s.get("c", "") for s in out)


def test_tabular_becomes_latex_segment():
    segs = [{"t": "text",
             "c": "数据如下： \\begin{center}\\renewcommand{\\arraystretch}{1.3}"
                  "\\begin{tabular}{c|cc}\\hline X&0&1\\\\ \\hline P&.5&.5\\\\ \\hline\\end{tabular}"
                  "\\end{center} 求期望"}]
    out, extras = repair_fields(segs, _mp)
    lat = [s for s in out if s["t"] == "latex"
           and ("array" in s["c"] or "tabular" in s["c"])]
    assert lat, "tabular 应转成 latex 段"
    texts = "".join(s["c"] for s in out if s["t"] == "text")
    assert "tabular" not in texts and "renewcommand" not in texts
    assert "数据如下" in texts and "求期望" in texts


def test_multicolumn_stripped():
    segs = [{"t": "text", "c": "\\begin{tabular}{|c|}\\multicolumn{13}{c}{合计}\\\\1\\end{tabular}"}]
    out, _ = repair_fields(segs, _mp)
    lat = [s for s in out if s["t"] == "latex"][0]["c"]
    assert "multicolumn" not in lat and "合计" in lat


def test_answer_env_migrated():
    """\\begin{answer}D\\end{answer} 环境形态从 stem 剥出迁 answer。"""
    segs = [{"t": "text", "c": "下列判断正确的是 \\begin{answer}D\\end{answer} 请作答"}]
    out, extras = repair_fields(segs, _mp)
    flat = "".join(s["c"] for s in out if s["t"] == "text")
    assert "answer" not in flat and "下列判断正确的是" in flat and "请作答" in flat
    assert extras.get("answer") == ["D"]


def test_migrated_solution_gets_full_pipeline():
    """迁移自 stem 的 solution 内容须经完整结构管线:enumerate 序号化,
    否则命令原样落进解析(全库 264 个残留的来源)。"""
    from pipeline.reparse import repair_question
    stem = [{"t": "text", "c": "证明: \\begin{solution} \\begin{enumerate} "
                             "\\item 先证 $a>b$; \\item 再证 $c>d$. "
                             "\\end{enumerate} \\end{solution} 完毕"}]
    q = {"stem": stem, "answer": [], "analysis": [], "options": []}
    repair_question(q, lambda p: None)
    ana = "".join(s["c"] for s in q["analysis"] if s["t"] == "text")
    assert "enumerate" not in ana and "\\item" not in ana
    assert "(1)" in ana and "(2)" in ana and "先证" in ana


def test_pretty_linebreaks_text_only():
    """pretty 换行只作用于 text 段:半角句点(源库解析大量使用)在
    后随空白时换行,latex 段内小数点不受影响;全角句读直接换行。"""
    segs = [{"t": "text", "c": "先看定义. 再算 "},
            {"t": "latex", "c": "3.14+2.86"},
            {"t": "text", "c": " 得证。又及；完毕"}]
    out, _ = repair_fields(segs, _mp, pretty=True)
    texts = [s["c"] for s in out if s["t"] == "text"]
    assert "定义.\n" in texts[0]           # 半角句点后随空白 → 换行
    assert texts[0].endswith("\n") or texts[0].endswith("再算 ")
    lat = [s["c"] for s in out if s["t"] == "latex"]
    assert "3.14+2.86" in lat[0]           # 公式内小数点不动
    assert "得证。\n" in texts[-1] and "又及；\n" in texts[-1]


def test_latex_segment_boundary_dollar_stripped():
    """latex 段首尾带 $ 定界(历史中间态)不再触发安全阀放弃修复。"""
    segs = [{"t": "text", "c": "\\begin{enumerate} \\item 若 "},
            {"t": "latex", "c": "$x>0$"},
            {"t": "text", "c": " 则 \\item 否 \\end{enumerate}"}]
    out, _ = repair_fields(segs, _mp)
    flat = "".join(s["c"] for s in out if s["t"] == "text")
    assert "enumerate" not in flat and "(1)" in flat and "(2)" in flat
    lat = [s["c"] for s in out if s["t"] == "latex"]
    assert "x>0" in " ".join(lat)


def test_stray_item_removed():
    """环境已丢的散落 \\item:题干常已手写 (1)(2),兜底删标记保句子完整。"""
    segs = [{"t": "text", "c": "(1) 求概率； (2) 求期望； \\item 若改为不放回呢"}]
    out, _ = repair_fields(segs, _mp)
    flat = "".join(s["c"] for s in out if s["t"] == "text")
    assert "\\item" not in flat and "若改为不放回呢" in flat


def test_bare_array_env_wrapped_as_latex():
    """源库原生 \\begin{array} 无 $ 定界落 text 段:配对后包成 latex 段。"""
    segs = [{"t": "text", "c": "成绩表 \\begin{array}{cc} 1 & 2\\\\ 3 & 4\\end{array} 如上"}]
    out, _ = repair_fields(segs, _mp)
    lat = [s for s in out if s["t"] == "latex" and "array" in s.get("c", "")]
    assert lat and "1 & 2" in lat[0]["c"]
    texts = "".join(s["c"] for s in out if s["t"] == "text")
    assert "\\begin" not in texts and "成绩表" in texts and "如上" in texts


def test_table_units_with_dollar_not_torn():
    """表格单元被拆成 latex 段(拼回后表格内含 $..$):转 latex 段且不被重拆撕碎。"""
    segs = [{"t": "text", "c": "数阵 \\begin{array}{|c|} \\hline "},
            {"t": "latex", "c": "1"},
            {"t": "text", "c": " & "},
            {"t": "latex", "c": "-1"},
            {"t": "text", "c": " \\\\ \\hline \\end{array} 完"}]
    out, _ = repair_fields(segs, _mp)
    lat = [s["c"] for s in out if s["t"] == "latex"]
    whole = [c for c in lat if "\\begin{array}" in c]
    assert whole and "\\end{array}" in whole[0], "表格须完整落在同一 latex 段"
    assert "$" not in whole[0]  # 单元 $ 定界清除,重拆不再撕碎
    texts = "".join(s["c"] for s in out if s["t"] == "text")
    assert "\\begin" not in texts and "数阵" in texts and "完" in texts


def test_orphan_tabular_end_removed():
    """源库错乱的游离 \\end{tabular}:删除不残留。"""
    segs = [{"t": "text", "c": "A=1 \\end{tabular} 后续文字"}]
    out, _ = repair_fields(segs, _mp)
    flat = "".join(s["c"] for s in out if s["t"] == "text")
    assert "tabular" not in flat and "后续文字" in flat


def test_bare_aligned_wrapped_as_latex():
    """text 段完整 aligned 块(无 $ 定界):配对包成 latex 段。"""
    segs = [{"t": "text", "c": "则\n\\begin{aligned}\nP&=\\frac12\\\\\nQ&=\\frac13\n\\end{aligned}\n故得"}]
    out, _ = repair_fields(segs, _mp)
    lat = [s for s in out if s["t"] == "latex" and "aligned" in s.get("c", "")]
    assert lat and "P&=" in lat[0]["c"]
    texts = "".join(s["c"] for s in out if s["t"] == "text")
    assert "aligned" not in texts and "故得" in texts


def test_delimited_cases_not_torn():
    """latex 段内的 cases(拼回后已有 $ 定界)不得再包 $ 撕碎。"""
    segs = [{"t": "text", "c": "求函数 "},
            {"t": "latex", "c": "f(x)=\\begin{cases}\nx^2, & x\\ne0,\\\\\n0, & x=0\n\\end{cases}"},
            {"t": "text", "c": " 的导数."}]
    out, _ = repair_fields(segs, _mp)
    lat = [s["c"] for s in out if s["t"] == "latex"]
    whole = [c for c in lat if "\\begin{cases}" in c]
    assert whole and "\\end{cases}" in whole[0] and "f(x)=" in whole[0]
    texts = "".join(s["c"] for s in out if s["t"] == "text")
    assert "cases" not in texts and "求函数" in texts and "的导数" in texts


def test_examdisplay_becomes_latex():
    segs = [{"t": "text", "c": "方程为 \\examdisplaycases{}{ x=2\\cos\\theta,\\\\ y=4\\sin\\theta } 求之"}]
    out, _ = repair_fields(segs, _mp)
    lat = [s for s in out if s["t"] == "latex" and "cases" in s["c"]]
    assert lat and "x=2\\cos\\theta" in lat[0]["c"]
    texts = "".join(s["c"] for s in out if s["t"] == "text")
    assert "examdisplay" not in texts


def test_misc_commands_cleaned():
    segs = [{"t": "text", "c": "\\FloatBarrier 结束\\allowbreak\\begingroup X\\endgroup "
             "\\hspace{1.5em}后\\circled{1}，当"}]
    out, _ = repair_fields(segs, _mp)
    flat = "".join(s["c"] for s in out if s["t"] == "text")
    for gone in ("FloatBarrier", "allowbreak", "begingroup", "endgroup",
                 "hspace", "circled"):
        assert gone not in flat, gone
    assert "(1)" in flat


def test_answer_solution_migrated_from_stem():
    segs = [{"t": "text", "c": "求通项\\fillinblank{}. \\answer{2} \\begin{solution} 由题意得 "
             "$a_2=4$，故 $a_1=2$. \\end{solution}"}]
    out, ex = repair_fields(segs, _mp)
    flat = "".join(s["c"] for s in out if s["t"] == "text")
    assert "\\answer" not in flat and "solution" not in flat
    # 迁移内容经 extras 分流(由 repair_question 写入 answer/analysis 字段)
    assert ex.get("answer") == ["2"]
    assert ex.get("analysis") and "由题意得" in ex["analysis"][0]
