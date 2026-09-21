"""bookmaker 渲染与成册测试。"""
from bookmaker.render import (_fix_tex, collect_latex, render_latex_batch,
                              segs_to_html)


def _q():
    return [{"stem": [{"t": "text", "c": "已知"},
                      {"t": "latex", "c": "\\frac{1}{2}"}],
             "options": [{"label": "A", "segs": [{"t": "text", "c": "{1}"}]}],
             "answer": [{"t": "latex", "c": "x^2"}],
             "analysis": []}]


def test_collect_latex():
    assert set(collect_latex(_q())) == {("\\frac{1}{2}", False), ("x^2", False)}


def test_render_latex_batch():
    got = render_latex_batch([("\\frac{1}{2}", False), ("x^2", False)])
    assert "\\frac{1}{2}\x00False" in got
    assert "katex" in got["\\frac{1}{2}\x00False"]
    # 语法错误不整体失败:throwOnError:false 渲染为红色 katex-error 文本
    bad = render_latex_batch([("\\\\bad{", False)])
    assert "katex-error" in bad["\\\\bad{\x00False"]


def test_segs_to_html_render_and_fallback():
    rendered = {"\\frac{1}{2}\x00False": '<span class="katex">…</span>'}
    html = segs_to_html(_q()[0]["stem"], rendered)
    assert "已知" in html
    assert '<span class="katex">…</span>' in html
    # 降级:渲染表为空 → <code>
    html2 = segs_to_html(_q()[0]["stem"], {})
    assert "<code>" in html2
    # 转义
    html3 = segs_to_html([{"t": "text", "c": "a<b>&c"}], {})
    assert "a&lt;b&gt;&amp;c" in html3


def test_segs_to_html_img():
    html = segs_to_html([{"t": "img", "c": "/assets/x.png"}], {})
    assert '<img class="qimg" src="/assets/x.png">' in html


def test_fix_tex_imaginary_unit():
    # 源仓库把虚数单位写作 \i(非标准命令,KaTeX 拒绝)→ 定向替换为 i
    assert _fix_tex("\\frac{z}{\\i}=-1-\\i") == "\\frac{z}{i}=-1-i"
    # \int/\infty/\ln 等以 \i 开头的合法命令不受影响
    assert _fix_tex("\\int_0^1 x\\,dx + \\infty") == "\\int_0^1 x\\,dx + \\infty"


def test_collect_latex_applies_fix():
    q = [{"stem": [{"t": "latex", "c": "\\frac{z}{\\i}"}],
          "options": [], "answer": [], "analysis": []}]
    assert collect_latex(q) == [("\\frac{z}{i}", False)]


def test_segs_to_html_uses_fixed_key():
    rendered = {"\\frac{z}{i}\x00False": '<span class="katex">z/i</span>'}
    html = segs_to_html([{"t": "latex", "c": "\\frac{z}{\\i}"}], rendered)
    assert '<span class="katex">z/i</span>' in html
    assert "<code>" not in html


def test_render_no_mathml_layer():
    # output:'html' 只生成视觉层,MathML 无障碍层由前端 KaTeX CDN 负责
    got = render_latex_batch([("x^2", False)])
    assert "katex-mathml" not in got["x^2\x00False"]
