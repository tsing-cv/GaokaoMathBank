"""清洗与公式标准化:入库后处理题目的工序。

- 噪音:水印/来源/网址/推广文案
- 公式:\\(...\\) 与【...】统一为 $...$;$$..$$ 行内降级为 $..$
- 标点:句尾半角句点转全角
"""
import copy
import re

_NOISE = re.compile(r"(来源[:：][^\s]*|更多资料.*|下载地址.*|www\.\S+|http\S+|"
                    r"本资料.*|版权所有.*)")
# 各来源的公式定界统一
_LATEX_PAIRS = [
    (re.compile(r"\\\((.+?)\\\)"), r"$\1$"),   # \(x\) → $x$
    (re.compile(r"【(.+?)】"), r"$\1$"),        # 【x】 → $x$(部分门户习惯)
]
_PUNCT = {".": "。", ";": ";", "!": "!", "?": "?"}


def standardize_latex(text: str) -> str:
    for pat, rep in _LATEX_PAIRS:
        text = pat.sub(rep, text)
    # $$..$$ 成对的降级为 $..$(行内)
    text = re.sub(r"\$\$(.+?)\$\$", r"$\1$", text, flags=re.S)
    return text


def _norm_text(s: str) -> str:
    s = _NOISE.sub("", s)
    s = standardize_latex(s)
    # LaTeX 源 text 段残留的排版命令:\quad/\qquad → 全角空格,\text{..} 取内容
    s = re.sub(r"\\qquad|\\quad", "\u3000", s)
    s = re.sub(r"\\text\s*\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\dots\b|\.{3}", "…", s)
    s = re.sub(r"\s+", " ", s).strip()
    # 半角点后紧跟汉字 → 全角句号(句中);数字上下文(3.14)不动
    s = re.sub(r"\.(?=[一-鿿])", "。", s)
    if s.endswith(tuple(_PUNCT)):
        s = s[:-1] + _PUNCT[s[-1]]
    return s


def normalize_question(q: dict) -> dict:
    """入 pipeline 的题目 dict,原地修正并返回。"""
    for field in ("stem", "answer", "analysis"):
        for seg in q.get(field) or []:
            if seg["t"] == "text":
                seg["c"] = _norm_text(seg["c"])
            elif seg["t"] == "latex":
                seg["c"] = seg["c"].strip().strip("$").strip()
    for opt in q.get("options") or []:
        for seg in opt.get("segs") or []:
            if seg["t"] == "text":
                seg["c"] = _norm_text(seg["c"])
    return q


if __name__ == "__main__":
    # 全库清洗:逐题过 normalize_question 并回写
    from app.models import Question, SessionLocal

    with SessionLocal() as db:
        n = 0
        for q in db.query(Question).all():
            # 深拷贝再清洗:原地改 ORM 加载的对象后赋回同引用,
            # SQLAlchemy 变更检测判等会跳过 UPDATE(JSON 列不追踪原地修改)
            d = copy.deepcopy({"stem": q.stem, "answer": q.answer,
                               "analysis": q.analysis, "options": q.options})
            normalize_question(d)
            q.stem, q.answer, q.analysis, q.options = (
                d["stem"], d["answer"], d["analysis"], d["options"])
            n += 1
        db.commit()
        print(f"清洗 {n} 题")
