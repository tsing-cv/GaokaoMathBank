import pytest
from app.segments import (parse_segments, preview_segments, segments_to_text,
                          validate_segments)


def test_plain_text_becomes_single_text_segment():
    assert parse_segments("已知函数") == [{"t": "text", "c": "已知函数"}]


def test_inline_latex_extracted():
    segs = parse_segments("已知 $f(x)=x^2$,求导")
    assert {"t": "latex", "c": "f(x)=x^2"} in segs
    assert segs[0] == {"t": "text", "c": "已知 "}


def test_passthrough_valid_list():
    src = [{"t": "img", "c": "/assets/a.png"}]
    assert parse_segments(src) == src


def test_invalid_segment_raises():
    with pytest.raises(ValueError):
        validate_segments([{"t": "bad", "c": "x"}])


def test_to_text_join():
    segs = [{"t": "text", "c": "a"}, {"t": "latex", "c": "x^2"}, {"t": "img", "c": "/a.png"}]
    assert segments_to_text(segs) == "a $x^2$ [图]"


def test_preview_segments_truncates_on_boundaries():
    """预览截断只落在段边界:latex/img 段要么完整保留要么整段丢弃,
    绝不切半截(切半 + $..$ 定界会被 KaTeX 渲染成错位红字)。"""
    segs = [{"t": "text", "c": "已知函数"},
            {"t": "latex", "c": "f(x)=x^{100}"},
            {"t": "text", "c": "求其单调区间"}]
    # limit=16:恰好容纳 text(4)+latex(12),第三段放不下
    out = preview_segments(segs, 16)
    assert out[0] == {"t": "text", "c": "已知函数"}
    assert out[1] == {"t": "latex", "c": "f(x)=x^{100}"}  # 恰好放下的段完整
    assert out[-1] == {"t": "text", "c": "…"}             # 放不下的补省略号
    assert "求其单调区间" not in [s["c"] for s in out]
    # limit=6:连 latex 段都放不下 → 整段丢弃(绝不截半截公式)
    out6 = preview_segments(segs, 6)
    assert out6[0] == {"t": "text", "c": "已知函数"}
    assert all(s["t"] != "latex" for s in out6)
    # 宽裕 limit:原样返回
    assert preview_segments(segs, 200) == segs


def test_preview_segments_long_text_partial():
    """首段就是超长 text:允许只截该文本段(纯文本切半无害),
    避免预览空白;后续 latex 段整段丢弃。"""
    segs = [{"t": "text", "c": "已知" + "甲" * 20},
            {"t": "latex", "c": "x^2"}]
    out = preview_segments(segs, 5)
    assert out[0]["c"] == "已知甲甲甲"
    assert out[-1]["c"] == "…"
    assert all(s["t"] != "latex" for s in out)


def test_preview_segments_keeps_img():
    assert preview_segments([{"t": "img", "c": "/a.png"}], 10) == \
        [{"t": "img", "c": "/a.png"}]
