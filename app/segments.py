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


def preview_segments(segs: list[dict], limit: int = 100) -> list[dict]:
    """列表预览段:整段取舍,latex/img 段要么完整保留要么整段丢弃。

    早期实现(segments_to_plain)把 latex 段的 $ 定界剥掉以纯文本呈现,
    导致检索列表/相关题里公式源码裸奔(\\frac、\\lg 原样显示)。正确
    做法:预览也带 $..$ 交给 KaTeX 渲染,靠"截断只落在段边界"保证
    不会产生孤立 $(切半截公式 + 定界 = 错位红字)。超长 text 段允许
    切半(纯文本无定界问题),避免首段超长时预览空白。
    """
    out: list[dict] = []
    n = 0
    for s in segs:
        if s["t"] == "text":
            c = s.get("c") or ""
            if n + len(c) > limit:
                head = c[:limit - n].rstrip()
                if head:
                    out.append({"t": "text", "c": head})
                out.append({"t": "text", "c": "…"})
                return out
            out.append({"t": "text", "c": c})
            n += len(c)
        else:
            # img 显示为 [图] 记 3 字符;latex 按源码长度计
            ln = 3 if s["t"] == "img" else len(s.get("c") or "")
            if n + ln > limit:
                out.append({"t": "text", "c": "…"})
                return out
            out.append(dict(s))
            n += ln
    return out


# 图片类命令:\bitmapfigure[...]{img/...} 题图、\choicebitmap[...]{img/...} 选项图
_IMG_CMD = re.compile(r"\\(?:bitmapfigure|choicebitmap)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")


def split_images(segs: list[dict], map_path) -> list[dict]:
    """把分段中残留的图片类命令拆为独立 img 段。

    map_path(源相对路径 img/..) → web 路径(/assets/..),返回 None 表示
    无法解析——此时保留原文本不动,宁可显示命令也不丢图。返回新列表。
    """
    out: list[dict] = []
    for seg in segs:
        c = seg.get("c") or ""
        if "\\" not in c or not _IMG_CMD.search(c):
            out.append(seg)
            continue
        pos = 0
        for m in _IMG_CMD.finditer(c):
            web = map_path(m.group(1).strip())
            if web is None:
                continue
            if m.start() > pos:
                out.append({"t": seg["t"], "c": c[pos:m.start()]})
            out.append({"t": "img", "c": web})
            pos = m.end()
        if pos < len(c):
            out.append({"t": seg["t"], "c": c[pos:]})
    return out


# ---- 源库非标准 LaTeX 命令 → KaTeX 兼容 ----
# DxAThing 源用了一批自定义宏(\bs 向量粗体、\e 自然底、\i 虚数单位、
# \fillinblank 填空线、\circled 圈号、\choicebitmap 选项位图、\myarc 弧),
# KaTeX 一律 Undefined control sequence 且 throwOnError 默认 true 会中断
# 整页 auto-render,故入库清洗 + 成册渲染前统一走本函数。
_LATEX_FIXES = [
    # 源库普遍存在"命令与后随变量 e/i 之间空格丢失"的粘连笔误:
    # a\leqslante^{-1} 实为 a \leqslant e^{-1};i\cdoti 实为 i \cdot i。
    # 负向前瞻避免吞并后续字母;须置于 \e/\i 单字母规则之前。
    (re.compile(r"\\leqslante(?![a-zA-Z])"), r"\\leqslant e"),
    (re.compile(r"\\geqslante(?![a-zA-Z])"), r"\\geqslant e"),
    (re.compile(r"\\dfrace(?![a-zA-Z])"), r"\\dfrac{e}"),
    (re.compile(r"\\frace(?![a-zA-Z])"), r"\\frac{e}"),
    (re.compile(r"\\lne(?![a-zA-Z])"), r"\\ln e"),
    (re.compile(r"\\lee(?![a-zA-Z])"), r"\\le e"),
    (re.compile(r"\\leqe(?![a-zA-Z])"), r"\\leq e"),
    (re.compile(r"\\lge(?![a-zA-Z])"), r"\\lg e"),
    (re.compile(r"\\gee(?![a-zA-Z])"), r"\\ge e"),
    (re.compile(r"\\geqe(?![a-zA-Z])"), r"\\geq e"),
    (re.compile(r"\\neqe(?![a-zA-Z])"), r"\\neq e"),
    (re.compile(r"\\nee(?![a-zA-Z])"), r"\\ne e"),
    (re.compile(r"\\cdoti(?![a-zA-Z])"), r"\\cdot i"),
    (re.compile(r"\\cdote(?![a-zA-Z])"), r"\\cdot e"),
    (re.compile(r"\\pmi(?![a-zA-Z])"), r"\\pm i"),
    (re.compile(r"\\mpi(?![a-zA-Z])"), r"\\mp i"),
    (re.compile(r"\\lverti(?![a-zA-Z])"), r"\\lvert i"),
    # 粘连家族补充:\to e / \pi e / \pi i / \int e / \lambda e
    (re.compile(r"\\toe(?![a-zA-Z])"), r"\\to e"),
    (re.compile(r"\\pie(?![a-zA-Z])"), r"\\pi e"),
    (re.compile(r"\\pii(?![a-zA-Z])"), r"\\pi i"),
    (re.compile(r"\\inte(?![a-zA-Z])"), r"\\int e"),
    (re.compile(r"\\lambdae(?![a-zA-Z])"), r"\\lambda e"),
    # 向量粗体:\bs{a}、\bs n 与 \bs0(数字无花括号)三种形态
    (re.compile(r"\\bs\s*\{([^}]+)\}"), r"\\mathbf{\1}"),
    (re.compile(r"\\bs\s*([0-9A-Za-z])(?![a-zA-Z])"), r"\\mathbf{\1}"),
    # 单字母笔误:\e 自然对数底、\i 虚数单位(负向前瞻避免误伤
    # \epsilon/\int/\infty/\ln 等以 \e、\i 开头的合法命令)
    (re.compile(r"\\e(?![a-zA-Z])"), "e"),
    (re.compile(r"\\i(?![a-zA-Z])"), "i"),
    # 填空线
    (re.compile(r"\\fillinblank\s*(?:\{\})?"), r"\\underline{\\hspace{1em}}"),
    # 多选答案圈号
    (re.compile(r"\\circled\s*\{([^}]+)\}"), r"\\text{(\1)}"),
    # 选项位图引用(图片由分段层另行处理,latex 内降级为占位)
    (re.compile(r"\\choicebitmap\s*(?:\[[^\]]*\])?\s*\{[^}]*\}"), r"\\text{[图]}"),
    # 弧符号:KaTeX 0.16 无 \myarc/\overparen/\wideparen,用 \overset{\frown}
    # (后两者一并转换,覆盖早期清洗批次写入库的中间形态)
    (re.compile(r"\\myarc\s*\{([^}]+)\}"), r"\\overset{\\frown}{\1}"),
    (re.compile(r"\\overparen\s*\{([^}]+)\}"), r"\\overset{\\frown}{\1}"),
    (re.compile(r"\\wideparen\s*\{([^}]+)\}"), r"\\overset{\\frown}{\1}"),
    # KaTeX 无 tabular/split 环境(array/aligned 同语法)
    (re.compile(r"\\begin\{tabular\}"), r"\\begin{array}"),
    (re.compile(r"\\end\{tabular\}"), r"\\end{array}"),
    (re.compile(r"\\begin\{split\}"), r"\\begin{aligned}"),
    (re.compile(r"\\end\{split\}"), r"\\end{aligned}"),
    # 源表格 \hline 与内容粘连(\hlineN&)——KaTeX 会读成未定义命令
    (re.compile(r"\\hline(?=[A-Za-z0-9])"), r"\\hline "),
    # 行分隔 \\ 与 \hline 粘连(\\hline):补空格
    (re.compile(r"\\\\hline"), r"\\\\ \\hline"),
    # \hline 前缺行分隔(2\hline P):补 \\ (源库行分隔丢失)
    (re.compile(r"(?<=[0-9A-Za-z}\)])\\hline"), r"\\\\ \\hline"),
    # KaTeX 无 \makebox/\multirow/\parbox:取内容
    (re.compile(r"\\makebox\s*\[[^\]]*\]\s*\{([^}]*)\}"), r"\1"),
    (re.compile(r"\\makebox\s*\{([^}]*)\}"), r"\1"),
    (re.compile(r"\\multirow\s*\{[^}]*\}\s*\{[^}]*\}\s*\{([^}]*)\}"), r"\1"),
    (re.compile(r"\\parbox\s*\{[^}]*\}\s*\{([^}]*)\}"), r"\1"),
    # 波浪号命令 KaTeX 缺
    (re.compile(r"\\textasciitilde"), r"\\text{~}"),
    # latex 段内连续下划线(源库填空线笔误 f(0)=____):
    # KaTeX 要求 _ 后跟组,数学下标不会连续出现
    (re.compile(r"_{2,}"), r"\\underline{\\hspace{1em}}"),
    # 表内残留的 \(..\) 定界(数学模式里非法)
    (re.compile(r"\\\((.+?)\\\)"), r"\1"),
    # \tag 仅 display 模式可用,行内删
    (re.compile(r"\\tag\s*\{[^}]*\}"), ""),
    # 行尾孤立反斜杠(如 a_n\)——前面若是 \\ 则是合法换行,不动
    (re.compile(r"(?<!\\)\\$"), ""),
]


def fix_latex(tex: str) -> str:
    """清洗源库非标准 LaTeX 命令为 KaTeX 可渲染形式(幂等)。"""
    for pat, rep in _LATEX_FIXES:
        tex = pat.sub(rep, tex)
    # \hline 仅 array 环境内合法:按 begin/end{array} 区间判定,
    # 环境外(如段内先出现孤立 \hline 再接表格)删除
    if "\\hline" in tex:
        keep = [(m.start(), m.end()) for m in
                re.finditer(r"\\begin\{array\}.*?\\end\{array\}", tex, re.S)]

        def _drop(m):
            return m.group(0) if any(s <= m.start() < e for s, e in keep) else ""
        tex = re.sub(r"\\hline\s*", _drop, tex)
    # \\ 后的 [x,y) 形区间单元格会被 KaTeX 当作 \\ 的行距可选参数:
    # 非纯尺寸内容时补空格隔开;合法行距 \\[6pt] 保留
    def _brk(m):
        inner = m.group(1)
        if re.fullmatch(r"[-+\d.]+\s*(?:pt|em|ex|mm|cm)?", inner or ""):
            return m.group(0)
        return "\\\\ [" + (inner or "") + "]"
    tex = re.sub(r"\\\\\[([^\]\[]*)\]", _brk, tex)
    # 无闭 ] 的区间形态(\\[29.90,29.94):排除尺寸后补空格
    tex = re.sub(r"\\\\\[(?=[\[\d(])(?![-+\d.]+\s*(?:pt|em|ex|mm|cm)\])",
                 r"\\\\ [", tex)
    return tex
