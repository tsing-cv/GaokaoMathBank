"""LaTeX 真题源(DxAThing/Gaokao-Math-Problems-Compilation)→ 结构化题目。

源格式约定:
- \\chapter{卷名} / \\section{单选题|多选题|填空题|解答题...}
- \\begin{problem}...\\end{problem} 每题;\\choices {..}{..}{..}{..} 选项
- \\begin{answer}...\\end{answer} 答案;\\begin{solution}...\\end{solution} 解析
- 行内公式 \\(...\\),行间公式 \\[...\\],配图 \\includegraphics{img/...}

产出:分段 JSON(同 app.segments 约定);img 段的 c 为仓库相对路径,
由 run_collect 下载后替换为 /assets/... web 路径。
"""
import re

# 三种富元素:行内公式 / 行间公式 / 图片
_RICH = re.compile(
    r"\\(?P<inline>\((?P<ic>.+?)\\\))"        # \(...\)
    r"|\\(?P<display>\[(?P<dc>.+?)\\\])"      # \[...\]
    r"|\\includegraphics(?:\[[^\]]*\])?\{(?P<img>[^}]+)\}",
    re.S)

_SECTION_TYPE = [
    (re.compile(r"单选|多选|选择"), "选择"),
    (re.compile(r"填空"), "填空"),
    (re.compile(r"解答"), "解答"),
]

_ENV = re.compile(r"\\begin\{(problem|answer|solution)\}(.*?)\\end\{\1\}", re.S)
_CHOICES = re.compile(r"\\choices")
_CHAPTER = re.compile(r"\\chapter\{(.+?)\}")
_SECTION = re.compile(r"\\section\{(.+?)\}")


def _extract_braced(text: str, start: int) -> tuple[str, int]:
    """从 text[start]=='{' 提取平衡内容(忽略 \\{ \\} 转义)。"""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise ValueError("LaTeX 花括号不平衡")


def _split_choices(body: str) -> tuple[str, list[dict]]:
    """拆出题干与 \\choices 的四个选项(brace-aware)。"""
    m = _CHOICES.search(body)
    if not m:
        return body, []
    stem = body[:m.start()]
    rest = body[m.end():].lstrip()
    options: list[dict] = []
    labels = "ABCDEFGH"
    i = 0
    while i < len(rest) and rest[i] == "{" and len(options) < 8:
        content, end = _extract_braced(rest, i)
        options.append({"label": labels[len(options)],
                        "segs": to_segments(content)})
        rest = rest[end:].lstrip()
    return stem, options


def to_segments(text: str) -> list[dict]:
    """LaTeX 文本 → 分段 JSON(text/latex/img)。"""
    segs: list[dict] = []
    pos = 0
    for m in _RICH.finditer(text):
        if m.start() > pos:
            _plain = text[pos:m.start()].strip()
            if _plain:
                segs.append({"t": "text", "c": re.sub(r"\s+", " ", _plain)})
        if m.group("inline"):
            segs.append({"t": "latex", "c": m.group("ic").strip()})
        elif m.group("display"):
            segs.append({"t": "latex", "c": m.group("dc").strip()})
        else:
            segs.append({"t": "img", "c": m.group("img")})
        pos = m.end()
    if pos < len(text):
        _plain = text[pos:].strip()
        if _plain:
            segs.append({"t": "text", "c": re.sub(r"\s+", " ", _plain)})
    return segs


def _sec_type(section_title: str) -> str:
    for pat, t in _SECTION_TYPE:
        if pat.search(section_title):
            return t
    return "解答"


def parse_tex(tex: str, meta: dict) -> dict:
    """整卷 LaTeX → {**meta, questions:[...], _images:[...]}。"""
    chapter = _CHAPTER.search(tex)
    # 题型:section 推进;记录每个字符位置的当前题型
    cur_type = "解答"
    events = []  # (pos, type) 或 (pos, None=回到默认)
    for m in _SECTION.finditer(tex):
        events.append((m.start(), _sec_type(m.group(1))))

    def type_at(pos: int) -> str:
        t = "解答"
        for ep, et in events:
            if ep <= pos:
                t = et
            else:
                break
        return t

    questions: list[dict] = []
    pending: dict | None = None
    images: list[str] = []
    seq = 0
    for m in _ENV.finditer(tex):
        kind, body = m.group(1), m.group(2)
        if kind == "problem":
            seq += 1
            stem_raw, options = _split_choices(body)
            qtype = "选择" if options else type_at(m.start())
            stem = to_segments(stem_raw)
            images += [s["c"] for s in stem if s["t"] == "img"]
            pending = {"seq": seq, "qtype": qtype, "stem": stem,
                       "options": options, "answer": [], "analysis": []}
        elif kind == "answer" and pending is not None:
            pending["answer"] = to_segments(body)
        elif kind == "solution" and pending is not None:
            pending["analysis"] = to_segments(body)
            questions.append(pending)  # solution 结束一题
            pending = None
    # 收尾:无 solution 的题(个别年份可能缺解析)也要保留
    if pending is not None:
        questions.append(pending)

    name = chapter.group(1) if chapter else meta.get("name", "")
    return {**meta, "name": name or meta.get("name", ""),
            "questions": questions, "question_count": len(questions),
            "_images": sorted(set(images))}
