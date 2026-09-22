"""清洗与公式标准化:入库后处理题目的工序。

- 噪音:水印/来源/网址/推广文案
- 公式:\\(...\\) 与【...】统一为 $...$;$$..$$ 行内降级为 $..$
- 标点:句尾半角句点转全角
"""
import copy
import re
import shutil

from app import ROOT
from app.segments import fix_latex, split_images

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


def make_asset_resolver(raw_root=None, assets_dir=None):
    """图片 resolver:img/<年>/<卷>/x.png → 复制到 data/assets 并返回 web 路径。

    源文件缺失返回 None(split_images 会保留原文本)。幂等:目标已存在跳过。
    """
    from pathlib import Path
    raw_root = Path(raw_root) if raw_root else ROOT / "data/raw/github-gaokao-latex"
    assets_dir = Path(assets_dir) if assets_dir else ROOT / "data/assets"

    def resolve(src_rel: str) -> str | None:
        src = raw_root / src_rel
        if not src.is_file():
            return None
        rel = Path(src_rel)
        # img/2006/anhui/q1.png → assets/2006/anhui/q1.png(保留子目录防重名)
        target = assets_dir.joinpath(*rel.parts[1:]) if rel.parts[:1] == ("img",) \
            else assets_dir / rel
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        return "/" + target.relative_to(assets_dir.parent).as_posix()

    return resolve


def normalize_question(q: dict, resolve_img=None) -> dict:
    """入 pipeline 的题目 dict,原地修正并返回。

    resolve_img 给定时,先把图片类命令拆为 img 段(须在文本清洗之前,
    否则 _norm_text 的排版命令清洗会搅乱 \\bitmapfigure 的参数)。
    """
    if resolve_img is not None:
        for field in ("stem", "answer", "analysis"):
            q[field] = split_images(q.get(field) or [], resolve_img)
        for opt in q.get("options") or []:
            opt["segs"] = split_images(opt.get("segs") or [], resolve_img)
    for field in ("stem", "answer", "analysis"):
        for seg in q.get(field) or []:
            if seg["t"] == "text":
                seg["c"] = _norm_text(seg["c"])
            elif seg["t"] == "latex":
                seg["c"] = fix_latex(seg["c"].strip().strip("$").strip())
    for opt in q.get("options") or []:
        for seg in opt.get("segs") or []:
            if seg["t"] == "text":
                seg["c"] = _norm_text(seg["c"])
            elif seg["t"] == "latex":
                seg["c"] = fix_latex(seg["c"].strip().strip("$").strip())
    return q


if __name__ == "__main__":
    # 全库清洗:逐题过 normalize_question 并回写(含图片化)
    from app.models import Question, SessionLocal

    resolve = make_asset_resolver()
    with SessionLocal() as db:
        n = 0
        for q in db.query(Question).all():
            # 深拷贝再清洗:原地改 ORM 加载的对象后赋回同引用,
            # SQLAlchemy 变更检测判等会跳过 UPDATE(JSON 列不追踪原地修改)
            d = copy.deepcopy({"stem": q.stem, "answer": q.answer,
                               "analysis": q.analysis, "options": q.options})
            normalize_question(d, resolve_img=resolve)
            q.stem, q.answer, q.analysis, q.options = (
                d["stem"], d["answer"], d["analysis"], d["options"])
            n += 1
        db.commit()
        print(f"清洗 {n} 题")
