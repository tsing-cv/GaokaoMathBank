"""字段级结构修复:当初按 $..$ 拆段时,无 $ 定界的环境/命令整块落进
text 段(circlelist/enumerate/item/tabular/solution/answer/examdisplay*/
图片命令变体),以原文显示在页面上。本模块把字段拼回源文本做结构转换
后重新分段:

- 图片命令变体(texfigure/solutionfigure/bitmapinclude/FigureLayoutDeclare)
  → img 段(复用 resolver 复制到 assets)
- circlelist → ①②③ 序号;enumerate → (1)(2) 序号(跨段连续计数)
- tabular 整块 → latex 段(fix_latex 再转 array,KaTeX 可渲染)
- examdisplaycases{}{..} → cases;examdisplayaligned/chain/array → aligned
- \\answer{X} 与 \\begin{solution}..\\end{solution} 从字段剥出,
  由 repair_question 迁入 answer/analysis(追加,不覆盖)
- 杂项壳命令(center/minipage/renewcommand/FloatBarrier/...)清除
- pretty=True 时按句读插换行(解析字段层次显示,CSS pre-wrap 配合)
"""
import re

from app.segments import parse_segments

# 图片类命令全集(split_images 的段级版本处理 bitmapfigure/choicebitmap,
# 此处再覆盖 text 段常见变体)
_IMG_RE = re.compile(
    r"\\(?:bitmapfigure|choicebitmap|texfigure|solutionfigure|bitmapinclude"
    r"|FigureLayoutDeclare)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")
_IMG_PLACE = re.compile(r"\[IMG:([^\]]+)\]")
_CIRCLES = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"


def _read_group(s: str, i: int) -> tuple[str | None, int]:
    """s[i] 为 '{' 时读平衡花括号组(跳过 \\{ \\} 转义),返回 (内容, 末后下标)。"""
    if i >= len(s) or s[i] != "{":
        return None, i
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\" and j + 1 < len(s) and s[j + 1] in "{}\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return None, i


def _flatten(segs: list[dict]) -> str | None:
    """段列表 → 源文本(text 原样 / latex 包 $..$ / img 转 [IMG:] 占位)。

    latex 段首尾残留的 $ 定界(历史清洗中间态)先剥除;剥除后内容仍含
    $ 时返回 None(安全阀:重拆会错位,调用方放弃修复)。
    """
    parts = []
    for s in segs:
        if s["t"] == "text":
            parts.append(s.get("c") or "")
        elif s["t"] == "latex":
            c = (s.get("c") or "").strip().strip("$").strip()
            if "$" in c:
                return None
            parts.append("$" + c + "$")
        else:
            parts.append("[IMG:" + (s.get("c") or "") + "]")
    return "".join(parts)


def _number_items(s: str, env: str, fmt) -> str:
    r"""\begin{env}..\end{env} 内的 \item 序号化,跨多组环境各自重新计数。"""
    begin_t, end_t = "\\begin{%s}" % env, "\\end{%s}" % env
    parts = re.split(r"(\\begin\{%s\}|\\end\{%s\})" % (env, env), s)
    inside, idx, out = False, 0, []
    for p in parts:
        if p == begin_t:
            inside, idx = True, 0
        elif p == end_t:
            inside = False
        elif inside and p:
            def _sub(m):
                nonlocal idx
                idx += 1
                return fmt(idx)
            p = re.sub(r"\\item(?![a-zA-Z])", _sub, p)
        out.append(p)
    return "".join(out)


def _to_segs(text: str, pretty: bool = False) -> list[dict]:
    """清洗后文本 → 分段(图片占位还原 img 段)。

    pretty 时按句读在 text 段插换行(解析层次显示,配合 CSS pre-wrap):
    全角句读直接换;半角句点须后随空白才换(3.14、a.b 等数字/符号
    上下文不动)。只在 text 段做——latex 段里公式内的小数点不能碰。
    """
    segs = parse_segments(text)
    out = []
    for s in segs:
        if s["t"] != "text":
            out.append(s)
            continue
        pos = 0
        for m in _IMG_PLACE.finditer(s["c"]):
            if m.start() > pos:
                out.append({"t": "text", "c": s["c"][pos:m.start()]})
            out.append({"t": "img", "c": m.group(1)})
            pos = m.end()
        if s["c"][pos:]:
            out.append({"t": "text", "c": s["c"][pos:]})
    # 散落换行符只在 text 段清洗——表格/examdisplay 行分隔已包进
    # latex 段($..$ 定界),此处不会误伤
    cleaned = []
    for s in out:
        if s["t"] != "text":
            # 撕碎残留:IMG 占位落进 latex 段 → 还原 img 段;
            # 孤立 & 段(表格撕碎)直接删除
            m = _IMG_PLACE.fullmatch(s.get("c") or "")
            if m:
                cleaned.append({"t": "img", "c": m.group(1)})
                continue
            if s["t"] == "latex" and (s.get("c") or "").strip() in ("&", "}"):
                continue
            cleaned.append(s)
            continue
        s["c"] = re.sub(r"(?<!\\)\\\\", " ", s["c"])
        if pretty:
            s["c"] = re.sub(r"([。；?!])(?!\n)", r"\1\n", s["c"])
            s["c"] = re.sub(r"\.(?=[ \t])(?!\n)", ".\n", s["c"])
        cleaned.append(s)
    return cleaned


def _clean_colfmt(fmt: str) -> str:
    """KaTeX array 不支持 p{..}/@{..}/*{n}{..} 列格式,归一为 c/展开。"""
    def _star(m):
        return m.group(2) * int(m.group(1))
    fmt = re.sub(r"\*\s*\{(\d+)\}\s*\{([^}]*)\}", _star, fmt)
    fmt = re.sub(r"[pP]\s*\{[^}]*\}", "c", fmt)
    fmt = re.sub(r"@\s*\{[^}]*\}", "", fmt)
    return fmt or "c"


def _strip_orphan_env_ends(text: str, envs: tuple[str, ...] = ("tabular", "array")) -> str:
    r"""栈配对清扫:无对应 \begin 的游离 \end{env} 直接删除(源库错乱残留)。"""
    end_re = re.compile(r"\\end\{(%s)\}" % "|".join(envs))
    begin_re = re.compile(r"\\begin\{(%s)\}" % "|".join(envs))
    spans = [(m.start(), m.end(), m.group(1)) for m in end_re.finditer(text)]
    drop = []
    for e_start, e_end, env in spans:
        # 此 end 之前,该环境的 begin 计数须大于 end 计数才配对
        b = len(begin_re.findall(text[:e_start]))
        e = sum(1 for s in spans if s[0] < e_start)
        if b <= e:
            drop.append((e_start, e_end))
    for e_start, e_end in reversed(drop):
        text = text[:e_start] + text[e_end:]
    return text


def _dollar_spans(text: str) -> list[tuple[int, int]]:
    """全文 $ 按出现顺序两两配对成的区间(第1-2个$一对,第3-4个一对…)。"""
    pos = [m.start() for m in re.finditer(r"\$", text)]
    return [(pos[i], pos[i + 1]) for i in range(0, len(pos) - 1, 2)]


def _wrap_bare_envs(text: str, envs: tuple[str, ...] = ("aligned", "cases", "gathered")) -> str:
    r"""text 段中无 $ 定界的完整 \begin{env}..\end{env} 块包成 $..$。

    begin 位置若已落在某 $..$ 配对区间内(latex 段拼回的形态,环境
    常在公式中部如 $f(x)=\begin{cases}..$),再包一层会把定界切错位
    撕碎公式——须按区间判断而非看 begin 前一个字符。
    不配对时删壳降级为可读文本。
    """
    spans = _dollar_spans(text)
    for env in envs:
        BEGIN, END = "\\begin{%s}" % env, "\\end{%s}" % env
        out, i = [], 0
        while True:
            b = text.find(BEGIN, i)
            if b < 0:
                out.append(text[i:])
                break
            e = text.find(END, b + len(BEGIN))
            if any(s < b < t for s, t in spans):  # 已定界,原样跳过
                end_pos = e + len(END) if e >= 0 else b + len(BEGIN)
                out.append(text[i:end_pos])
                i = end_pos
                continue
            if e < 0:  # 不配对:删壳保留内容
                out.append(text[i:b])
                out.append(text[b + len(BEGIN):])
                i = len(text)
                break
            out.append(text[i:b])
            out.append("$%s%s%s$" % (BEGIN, text[b + len(BEGIN):e], END))
            i = e + len(END)
        text = "".join(out)
    return text


def _convert_tabulars(text: str, envs: tuple[str, ...] = ("tabular", "array")) -> str:
    """tabular/裸 array → $\\begin{array}..$ 段(栈式配对;不配对时降级纯文本)。

    非贪婪正则在 begin/end 不配对时会吞到下一个表格的 end,把两张表
    切错位——必须逐 begin 找最近 end 显式配对。
    """
    BEGIN_RE = re.compile(r"\\begin\{(%s)\}" % "|".join(envs))
    out, i = [], 0
    while True:
        m = BEGIN_RE.search(text, i)
        if not m:
            out.append(text[i:])
            break
        env = m.group(1)
        BEGIN, END = m.group(0), "\\end{%s}" % env
        b = m.start()
        e = text.find(END, b + len(BEGIN))
        nxt_m = BEGIN_RE.search(text, b + len(BEGIN))
        nxt = nxt_m.start() if nxt_m else -1
        j = b + len(BEGIN)
        while j < len(text) and text[j] in " \n\t":
            j += 1
        fmt, j2 = _read_group(text, j)
        if e < 0 or (0 <= nxt < e):
            # 不配对:壳与列格式删除,内容降级为可读文本
            out.append(text[i:b])
            stop = nxt if nxt >= 0 else len(text)
            body = text[(j2 if fmt is not None else j):stop]
            body = re.sub(r"\\(?:hline|cline\s*\{[^}]*\})", "", body)
            body = body.replace("&", "  ")
            out.append(body)
            i = stop
            continue
        if fmt is None:
            fmt, j2 = "c", j
        out.append(text[i:b])
        inner = text[j2:e]
        inner = re.sub(r"\\multicolumn\s*\{\d+\}\s*\{[^}]*\}\s*\{([^}]*)\}",
                       r"\1", inner)
        inner = re.sub(r"\\renewcommand\s*\{[^}]*\}\s*\{[^}]*\}", "", inner)
        inner = re.sub(r"\\cline\s*\{[^}]*\}", "", inner)
        # 表格单元可能被源采集拆成过 latex 段,拼回后内部残留 $..$ 定界;
        # 不清除会在重分段时把表格撕碎(单元格为数学模式,去 $ 无害)
        inner = inner.replace("$", "")
        out.append("$\\begin{array}{%s}%s\\end{array}$"
                   % (_clean_colfmt(fmt), inner))
        i = e + len(END)
    return "".join(out)


def _migrate_answer_solution(s: str, extras: dict) -> str:
    r"""剥出 \answer{X} 与 solution 环境(仅迁移标记,正文清理由调用方续做)。"""
    # \answer{X}:值迁移为 answer 字段段
    out, i = [], 0
    while True:
        m = re.compile(r"\\answer\s*(?:\[[^\]]*\])?").search(s, i)
        if not m:
            break
        j = m.end()
        while j < len(s) and s[j] in " \n\t":
            j += 1
        val, j2 = _read_group(s, j)
        if val is None:  # 形态不符,跳过该命令原样保留
            i = m.end()
            continue
        extras.setdefault("answer", []).append(val)
        out.append(s[i:m.start()])
        i = j2
    out.append(s[i:])
    s = "".join(out)
    # \begin{solution}..\end{solution} 与 \begin{answer}..\end{answer}
    # 环境整块迁移(未闭合则取到尾)
    for env, key in (("solution", "analysis"), ("answer", "answer")):
        m = re.search(r"\\begin\{%s\}" % env, s)
        if m:
            end = re.search(r"\\end\{%s\}" % env, s)
            body = s[m.end():end.start() if end else len(s)]
            extras.setdefault(key, []).append(body)
            s = s[:m.start()] + (s[end.end():] if end else "")
    return s


def repair_fields(segs: list[dict], map_path, pretty: bool = False):
    """单字段结构修复:返回 (新段列表, extras)。

    extras = {"answer": [原文], "analysis": [原文]}(由 repair_question 分流)。
    """
    text = _flatten(segs)
    if text is None:
        return segs, {}

    extras: dict = {}
    text = _migrate_answer_solution(text, extras)

    # 先合并"已拆 img 段的残留壳":\cmd{ [IMG:..] } → [IMG:..]
    # (上一轮 split_images 把参数拆成了 img 段,壳留在相邻 text 段)
    text = re.sub(
        r"\\(?:bitmapfigure|choicebitmap|texfigure|solutionfigure"
        r"|bitmapinclude|FigureLayoutDeclare)\s*(?:\[[^\]]*\])?\s*"
        r"\{\s*(\[IMG:[^\]]+\])\s*\}", r"\1", text)
    # 图片命令 → 占位(resolver 失败保留原文)
    def _img(m):
        web = map_path(m.group(1).strip()) if map_path else None
        return "[IMG:%s]" % web if web else m.group(0)
    text = _IMG_RE.sub(_img, text)
    text = re.sub(r"\\examfiguregroup\s*(?:\[[^\]]*\])?", "", text)

    # examdisplay* → cases/aligned 公式
    out, i = [], 0
    while True:
        m = re.compile(r"\\examdisplay(\w+)\s*").search(text, i)
        if not m:
            break
        j, args = m.end(), []
        for _ in range(2 if m.group(1) == "cases" else 1):
            while j < len(text) and text[j] in " \n\t":
                j += 1
            val, j = _read_group(text, j)
            if val is None:
                args.append("")
                break
            args.append(val)
        env = "cases" if m.group(1) == "cases" else "aligned"
        out.append((m.start(), j, "$\\begin{%s}%s\\end{%s}$"
                    % (env, args[-1] if args else "", env)))
        i = j
    for start, end, rep in reversed(out):
        text = text[:start] + rep + text[end:]

    # tabular/裸 array 整块 → latex 段(先清游离 end,再配对扫描 + 列格式归一)
    text = _strip_orphan_env_ends(text)
    text = _convert_tabulars(text)
    # 无 $ 定界的完整 aligned/cases/gathered 块 → latex 段
    text = _wrap_bare_envs(text)

    # 列表序号化
    text = _number_items(text, "circlelist",
                         lambda n: " %s " % (_CIRCLES[n-1] if n <= len(_CIRCLES) else "(%d)" % n))
    text = _number_items(text, "enumerate", lambda n: " (%d) " % n)
    text = re.sub(r"\\(?:begin|end)\{(?:circlelist|enumerate)\}", "", text)
    # 环境已丢的散落 \item(题干常已手写 (1)(2) 编号):删标记保句子完整
    text = re.sub(r"\\item(?![a-zA-Z])", " ", text)

    # 杂项壳/排版命令
    text = re.sub(r"\\begin\{center\}|\\end\{center\}|\\begin\{minipage\}"
                  r"|\\end\{minipage\}|\\FloatBarrier|\\allowbreak"
                  r"|\\begingroup|\\endgroup|\\centering", "", text)
    # \parbox{宽度}{内容}:删壳与宽度参数,内容保留
    text = re.sub(r"\\parbox\s*\{[^}]*\}", "", text)
    text = re.sub(r"\\renewcommand\s*\{[^}]*\}\s*\{[^}]*\}", "", text)
    text = re.sub(r"\\circled\s*\{([^}]*)\}", r"(\1)", text)
    text = re.sub(r"\\fillinblank\s*(?:\{\})?", "____", text)
    text = re.sub(r"\\hspace\s*\{[^}]*\}", " ", text)
    text = re.sub(r"\\linewidth", "", text)

    # $$..$$ → $..$(parse_segments 只认单定界)
    text = re.sub(r"\$\$(.+?)\$\$", r"$\1$", text, flags=re.S)

    return _to_segs(text, pretty=pretty), extras


def _plain_segs(src: str) -> list[dict]:
    """迁移原文 → 分段(含 $..$ 拆 latex,与主字段同规则)。"""
    return _to_segs(re.sub(r"\$\$(.+?)\$\$", r"$\1$", src, flags=re.S))






def repair_question(q: dict, resolve_img) -> dict:
    """整题修复:各字段结构修复 + answer/solution 迁移分流(追加不覆盖)。

    迁移内容须经完整结构管线(solution 原文里的 enumerate/circlelist/
    表格若只拆段不转换,命令会原样落进解析字段)。
    """
    extras_all = {"answer": [], "analysis": []}
    for f in ("stem", "answer", "analysis"):
        segs, ex = repair_fields(q.get(f) or [], resolve_img,
                                 pretty=(f == "analysis"))
        q[f] = segs
        extras_all["answer"].extend(ex.get("answer", []))
        extras_all["analysis"].extend(ex.get("analysis", []))
    for opt in q.get("options") or []:
        opt["segs"], _ = repair_fields(opt.get("segs") or [], resolve_img)
    for f in ("answer", "analysis"):
        migrated = []
        for v in extras_all[f]:
            segs, _ = repair_fields(_plain_segs(v), resolve_img,
                                    pretty=(f == "analysis"))
            migrated.extend(segs)
        q[f] = (q.get(f) or []) + migrated
    return q
