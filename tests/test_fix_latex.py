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
