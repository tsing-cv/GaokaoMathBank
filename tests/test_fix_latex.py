"""fix_latex:源库非标准 LaTeX 命令的 KaTeX 兼容清洗。"""
from app.segments import fix_latex


def test_bs_vector_bold():
    # 向量粗体 \bs{a}/\bs n → \mathbf
    assert fix_latex("\\bs{a}\\cdot\\bs{b}") == "\\mathbf{a}\\cdot\\mathbf{b}"
    assert fix_latex("\\bs n_1\\cdot\\bs n_2") == \
        "\\mathbf{n}_1\\cdot\\mathbf{n}_2"
    assert fix_latex("\\bs{u} \\cdot \\bs{v}") == \
        "\\mathbf{u} \\cdot \\mathbf{v}"


def test_e_and_i_single_letters():
    # 自然对数底 \e / 虚数单位 \i → 裸字母;不误伤 \epsilon/\int/\infty
    assert fix_latex("3^{\\e}") == "3^{e}"
    assert fix_latex("\\frac{z}{\\i}=-1-\\i") == "\\frac{z}{i}=-1-i"
    assert fix_latex("\\epsilon \\int_0^1 x\\,dx + \\infty") == \
        "\\epsilon \\int_0^1 x\\,dx + \\infty"


def test_fillinblank():
    assert fix_latex("S_1+S_2=\\fillinblank{}") == \
        "S_1+S_2=\\underline{\\hspace{1em}}"
    assert fix_latex("A\\cup B=\\fillinblank") == \
        "A\\cup B=\\underline{\\hspace{1em}}"


def test_circled():
    # 多选答案圈号 \circled{2}\circled{4} → (2)(4)
    assert fix_latex("\\circled{2}\\circled{4}") == "\\text{(2)}\\text{(4)}"


def test_myarc():
    assert fix_latex("\\myarc{CD}") == "\\overset{\\frown}{CD}"
    # 早期批次写入库的 \overparen/\wideparen 中间形态同样转换
    assert fix_latex("\\overparen{AB}") == "\\overset{\\frown}{AB}"
    assert fix_latex("\\wideparen{AB}") == "\\overset{\\frown}{AB}"


def test_glued_variable_commands():
    """源库"命令与后随变量 e/i 空格丢失"粘连笔误的还原。"""
    # \leqslant + e
    assert fix_latex("a\\leqslante^{-1}") == "a\\leqslant e^{-1}"
    assert fix_latex("ae-e^2\\leqslante^2") == "ae-e^2\\leqslant e^2"
    assert fix_latex("x\\geqslante^2") == "x\\geqslant e^2"
    # \dfrac + e(e 是分子,后随单 token 为分母)
    assert fix_latex("\\left(\\dfrace3\\right)^x") == \
        "\\left(\\dfrac{e}3\\right)^x"
    # \ln/\lg/\cdot/\pm 与变量粘连
    assert fix_latex("y=e\\lne=e") == "y=e\\ln e=e"
    assert fix_latex("i\\cdoti=-1") == "i\\cdot i=-1"
    assert fix_latex("z=1\\pmi") == "z=1\\pm i"
    assert fix_latex("w\\lverti") == "w\\lvert i"
    # 不误伤合法命令:\left/\leftarrow 不含 \lee 等粘连形态
    assert fix_latex("\\leftarrow\\ne x") == "\\leftarrow\\ne x"


def test_bs_digit_form():
    # \bs0:数字无花括号的向量 0
    assert fix_latex("\\bs0+\\overrightarrow{OA}") == \
        "\\mathbf{0}+\\overrightarrow{OA}"


def test_trailing_lone_backslash():
    assert fix_latex("a_n\\") == "a_n"
    # \\ 换行保留
    assert fix_latex("x\\\\") == "x\\\\"


def test_choicebitmap_to_text():
    # 选项位图:latex 段内先降级为占位(图片由分段层另行处理)
    out = fix_latex("\\choicebitmap[width=0.15\\paperwidth]{img/2010/x.png}")
    assert "choicebitmap" not in out
    assert "img/" not in out


def test_tabular_to_array():
    src = "\\begin{tabular}{c|ccc}\nX&0&1&2\\\\ \\hline\nP&0.5\n\\end{tabular}"
    out = fix_latex(src)
    assert "\\begin{array}{c|ccc}" in out
    assert "tabular" not in out
    # 表内的 \\(..\\) 定界去除
    src2 = "\\begin{tabular}{c}\\(\\xi\\)&1\\end{tabular}"
    assert "\\xi" in fix_latex(src2) and "\\(" not in fix_latex(src2)


def test_split_to_aligned_and_tag():
    assert fix_latex("\\begin{split}\nf(x)&=x\\\\\n&=y\n\\end{split}") == \
        "\\begin{aligned}\nf(x)&=x\\\\\n&=y\n\\end{aligned}"
    assert fix_latex("q-p=1. \\tag{1}") == "q-p=1. "


def test_idempotent():
    s = "\\bs{a}\\cdot\\fillinblank{}"
    once = fix_latex(s)
    assert fix_latex(once) == once


def test_blank_underscores_to_underline():
    """latex 段内连续下划线(源库填空线笔误):KaTeX 要求 _ 后跟组。"""
    out = fix_latex("f(0)=____")
    assert out == "f(0)=\\underline{\\hspace{1em}}"
    # 单下标不动
    assert fix_latex("a_1+b_{2}") == "a_1+b_{2}"


def test_hline_glued_to_content():
    """源表格 \\hline 与内容粘连(\\hlineN&):补空格,避免 KaTeX 读成
    未定义命令 \\hlineN。"""
    src = "\\begin{array}{cc} \\hlineN& 0 \\\\ \\hline \\end{array}"
    out = fix_latex(src)
    assert "\\hline N" in out and "\\hlineN" not in out


def test_makebox_multirow_stripped():
    """KaTeX 无 \\makebox/\\multirow:取内容。"""
    assert fix_latex("\\makebox[3.0cm]{函数}") == "函数"
    assert fix_latex("\\makebox[0.8cm]{}") == ""
    assert fix_latex("\\multirow{2}{*}{自然状况}") == "自然状况"


def test_more_glued_command_pairs():
    """粘连家族新成员:\\to e/\\pi e/\\pi i/\\int e/\\lambda e。"""
    assert fix_latex("x\\toe") == "x\\to e"
    assert fix_latex("\\pie^{2}") == "\\pi e^{2}"
    assert fix_latex("\\pii") == "\\pi i"
    assert fix_latex("\\int_0^1 x\\,\\mathrm{d}x,\\quad \\lambdae") .endswith("\\lambda e")


def test_hline_outside_array_removed():
    """\\hline 仅 array 支持:aligned 等环境内的删,array 内保留。"""
    assert fix_latex("\\begin{aligned} a \\\\ \\hline b \\end{aligned}") == \
        "\\begin{aligned} a \\\\ b \\end{aligned}"
    assert "\\hline" in fix_latex("\\begin{array}{c} a \\\\ \\hline b \\end{array}")
    # 段内含 array,但 \hline 在 array 之外:外的删,内的留
    mixed = "x \\hline \\begin{array}{c} a \\\\ \\hline b \\end{array}"
    out = fix_latex(mixed)
    assert out.count("\\hline") == 1 and out.endswith("\\end{array}")


def test_parbox_and_bare_makebox_and_tilde():
    assert fix_latex("\\parbox{2cm}{内容}") == "内容"
    assert fix_latex("\\makebox{甲}") == "甲"
    assert fix_latex("x\\textasciitilde y") == "x\\text{~} y"


def test_rowbreak_glued_hline():
    """源表格 \\\\ \\hline 空格丢失成 \\\\hline:array 内补空格;
    array 外(如孤段)hline 按环境外规则删除。"""
    assert fix_latex("\\begin{array}{c} x \\\\hline y \\end{array}") == \
        "\\begin{array}{c} x \\\\ \\hline y \\end{array}"
    assert fix_latex("a \\\\hline b") == "a \\\\ b"


def test_rowbreak_bracket_not_size():
    r"""\\\\ 后随区间单元格 [29.9,30) 会被 KaTeX 当行距参数:补空格;
    合法行距 \\\\[6pt] 保留。"""
    assert fix_latex("12\\\\[29.90,29.94)&63") == "12\\\\ [29.90,29.94)&63"
    assert fix_latex("a\\\\[6pt]b") == "a\\\\[6pt]b"
