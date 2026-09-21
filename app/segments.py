"""题干富文本分段 JSON 的解析与校验。

统一格式:每段 {"t": "text|latex|img", "c": "..."}。
- text: 纯文本
- latex: LaTeX 公式(不带 $ 定界符)
- img: web 路径(/assets/...)
"""
import json
import re

# 行内 $...$ 公式(非贪婪)
_LATEX_RE = re.compile(r"\$([^$]+?)\$")

VALID_TYPES = {"text", "latex", "img"}


def parse_segments(src) -> list[dict]:
    """把字符串或已有分段列表规范化为分段数组。"""
    if src is None:
        return []
    if isinstance(src, list):
        segs = [dict(s) for s in src]
        validate_segments(segs)
        return segs
    if not isinstance(src, str):
        raise TypeError(f"segments 源必须是 str/list,得到 {type(src)}")
    segs: list[dict] = []
    pos = 0
    for m in _LATEX_RE.finditer(src):
        if m.start() > pos:
            segs.append({"t": "text", "c": src[pos:m.start()]})
        segs.append({"t": "latex", "c": m.group(1).strip()})
        pos = m.end()
    if pos < len(src):
        segs.append({"t": "text", "c": src[pos:]})
    return segs


def validate_segments(segs: list[dict]) -> None:
    for s in segs:
        if set(s.keys()) != {"t", "c"} or s["t"] not in VALID_TYPES:
            raise ValueError(f"非法分段: {s!r}")


def segments_to_text(segs: list[dict]) -> str:
    """分段转纯文本(FTS 索引用):latex 还原 $...$,图片记 [图]。"""
    out = []
    for s in segs:
        if s["t"] == "text":
            out.append(s["c"])
        elif s["t"] == "latex":
            out.append(f"${s['c']}$")
        else:
            out.append("[图]")
    return " ".join(out)


def dumps(segs: list[dict]) -> str:
    return json.dumps(segs, ensure_ascii=False)
