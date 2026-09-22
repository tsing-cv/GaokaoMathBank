"""split_images:把 text 段中残留的图片类命令拆为独立 img 段。"""
from app.segments import split_images


def _mp(p):
    # 模拟 resolver:img/a/b.png → /assets/a/b.png;源缺失(gone)返回 None
    if "gone" in p:
        return None
    return "/assets/" + p[len("img/"):] if p.startswith("img/") else None


def test_bitmapfigure_split():
    segs = [{"t": "text",
             "c": "如图 \\bitmapfigure[max width=0.88\\linewidth]{img/2006/a/q1.png} 求体积"}]
    out = split_images(segs, _mp)
    assert out == [
        {"t": "text", "c": "如图 "},
        {"t": "img", "c": "/assets/2006/a/q1.png"},
        {"t": "text", "c": " 求体积"},
    ]


def test_choicebitmap_at_tail():
    # 选项位图挂在题干尾部(韦恩图四选一形态)
    segs = [{"t": "text", "c": "关系的韦恩（Venn）图是（ ） "
             "\\choicebitmap[width=0.9\\linewidth]{img/2009/b/q1_venn.png}"}]
    out = split_images(segs, _mp)
    assert out[-1] == {"t": "img", "c": "/assets/2009/b/q1_venn.png"}
    assert "choicebitmap" not in out[0]["c"]


def test_image_at_start_no_empty_text():
    segs = [{"t": "text", "c": "\\bitmapfigure{img/x/y.png}如上图"}]
    out = split_images(segs, _mp)
    assert out == [{"t": "img", "c": "/assets/x/y.png"},
                   {"t": "text", "c": "如上图"}]


def test_multiple_images_in_one_segment():
    segs = [{"t": "text",
             "c": "\\bitmapfigure{img/a/1.png}和\\bitmapfigure{img/a/2.png}"}]
    out = split_images(segs, _mp)
    assert [s["t"] for s in out] == ["img", "text", "img"]
    assert out[1]["c"] == "和"


def test_unresolvable_path_kept_verbatim():
    # resolver 返回 None(源文件缺失)时保留原文,不丢数据
    segs = [{"t": "text", "c": "见 \\bitmapfigure{img/gone.png} 图"}]
    out = split_images(segs, _mp)
    assert out == segs


def test_latex_segment_defensive():
    # latex 段中若残留图片命令,同样拆出,剩余部分保持 latex
    segs = [{"t": "latex", "c": "x=1 \\bitmapfigure{img/a/f.png}"}]
    out = split_images(segs, _mp)
    assert {"t": "img", "c": "/assets/a/f.png"} in out
    assert any(s["t"] == "latex" and "x=1" in s["c"] for s in out)


def test_plain_segments_untouched():
    segs = [{"t": "text", "c": "无图"},
            {"t": "latex", "c": "x^2"},
            {"t": "img", "c": "/assets/exists.png"}]
    assert split_images(segs, _mp) == segs
