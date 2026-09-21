import pytest
from app.segments import parse_segments, segments_to_text, validate_segments


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
