"""汇编成册:题册 + 答案册分离,weasyprint 输出 PDF。

三种成册:
- build_paper_book:整卷(试卷库入口)
- build_topic_book:知识点专题(题量上限可配)
- build_custom_book:自选题单(question id 列表)
"""
from datetime import date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import ASSETS_DIR, BOOKS_DIR
from bookmaker.render import collect_latex, render_latex_batch, segs_to_html

_CSS = """
@page { size: A4; margin: 2cm 1.8cm;
        @bottom-center { content: counter(page); font-size: 9pt; color: #666; } }
body { font-family: 'Songti SC', 'Noto Serif SC', serif; font-size: 11pt;
       line-height: 1.8; color: #111; }
h1.cover-title { font-size: 22pt; text-align: center; margin-top: 35%;
                 page-break-after: always; }
.cover-sub { text-align: center; color: #444; margin-top: 8px; }
h2.part { page-break-before: always; font-size: 15pt; border-bottom: 2px solid #1a3a5c;
          padding-bottom: 4px; color: #1a3a5c; }
.q { page-break-inside: avoid; margin: 0 0 16px; }
.qno { font-weight: bold; margin-right: 6px; }
.qtype { color: #777; font-size: 9pt; }
.opts { margin: 6px 0 0 2em; }
.opt { margin: 2px 0; }
.ans-key { page-break-before: always; }
table.key { border-collapse: collapse; width: 100%; }
table.key td, table.key th { border: 1px solid #999; padding: 4px 8px;
                             text-align: center; font-size: 10pt; }
.dp { text-align: center; margin: 6px 0; }
code { font-family: 'Menlo', monospace; font-size: 10pt; background: #f4f4ee; }
.qimg { max-width: 88%; }
.a-block { margin: 8px 0 0 2em; }
.src { color: #777; font-size: 9pt; margin-top: 20px; text-align: center; }
"""


def _load_questions(db: Session, where_sql: str, params: dict) -> list[dict]:
    rows = db.execute(text(
        "SELECT q.id, q.seq, q.qtype, q.stem, q.options, q.answer, q.analysis, "
        "p.year, p.name AS paper_name, p.source_name, p.source_url "
        "FROM questions q JOIN papers p ON p.id = q.paper_id "
        f"WHERE {where_sql} ORDER BY p.year, p.name, q.seq"), params).all()
    import json as _json

    def j(v):
        return _json.loads(v) if isinstance(v, str) else (v or [])

    return [{"id": r.id, "seq": r.seq, "qtype": r.qtype, "stem": j(r.stem),
             "options": j(r.options), "answer": j(r.answer),
             "analysis": j(r.analysis), "year": r.year,
             "paper_name": r.paper_name, "source_name": r.source_name,
             "source_url": r.source_url} for r in rows]


def _fix_img_src(html: str) -> str:
    """/assets/... web 路径 → file:// 绝对路径(weasyprint 需要本地可寻址)。"""
    return html.replace('src="/assets/', f'src="{ASSETS_DIR}/')


def build_book_html(title: str, subtitle: str, questions: list[dict],
                    with_answers: bool, source_note: str = "") -> str:
    """组装成册 HTML(题册 with_answers=False / 答案册 True)。"""
    rendered = render_latex_batch(collect_latex(questions))
    parts = [f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<link rel="stylesheet" href="katex.min.css"><style>{_CSS}</style></head><body>
<h1 class="cover-title">{title}</h1>
<div class="cover-sub">{subtitle}</div>
<div class="cover-sub">{date.today().isoformat()} · 共 {len(questions)} 题</div>
<h2 class="part">{'答案与解析' if with_answers else '试题'}</h2>"""]
    key_rows: list[str] = []
    for i, q in enumerate(questions, 1):
        head = (f'<span class="qno">{i}.</span>'
                f'<span class="qtype">[{q["qtype"]}]</span>')
        body = f'<div class="tx">{segs_to_html(q["stem"], rendered)}</div>'
        opts = ""
        if q["options"]:
            li = "".join(
                f'<div class="opt"><b>{o["label"]}.</b>'
                f'{segs_to_html(o.get("segs") or [], rendered)}</div>'
                for o in q["options"])
            opts = f'<div class="opts">{li}</div>'
        ans = ""
        if with_answers:
            blocks = []
            if q["answer"]:
                blocks.append(f'<div class="a-block"><b>答案:</b>'
                              f'{segs_to_html(q["answer"], rendered)}</div>')
            if q["analysis"]:
                blocks.append(f'<div class="a-block"><b>解析:</b>'
                              f'{segs_to_html(q["analysis"], rendered)}</div>')
            ans = f'<div class="ans">{"".join(blocks)}</div>' if blocks else \
                  '<div class="a-block">答案待补</div>'
        elif q["answer"]:
            # 题册末尾速查表用
            from app.segments import segments_to_text
            key_rows.append(f"<tr><td>{i}</td><td>"
                            f"{segments_to_text(q['answer'])[:30]}</td></tr>")
        parts.append(f'<div class="q">{head}{body}{opts}{ans}</div>')
    tail = f'<div class="src">{source_note}</div></body></html>'
    if not with_answers and key_rows:
        table = ('<h2 class="part">答案速查</h2><table class="key"><tr><th>题号'
                 f'</th><th>答案</th></tr>{"".join(key_rows)}</table>')
        parts.append(table)
    parts.append(tail)
    return _fix_img_src("".join(parts))


def html_to_pdf(html: str, out: Path) -> Path:
    """子进程调 pdf_worker 渲染。

    weasyprint+pango 在本机进程清理阶段可能 SIGABRT(PDF 已完整写出),
    隔离在子进程跑,判定以产物存在为准,不信任退出码。
    """
    import subprocess
    import sys
    import tempfile
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8") as tf:
        tf.write(html)
        tmp = tf.name
    try:
        subprocess.run(
            [sys.executable, "-m", "bookmaker.pdf_worker", tmp, str(out)],
            cwd=str(Path(__file__).resolve().parent.parent),
            capture_output=True, timeout=600)
    finally:
        Path(tmp).unlink(missing_ok=True)
    if not out.is_file():
        raise RuntimeError("PDF 生成失败(worker 未产出文件)")
    return out


def _make_pair(db_title: str, slug: str, questions: list[dict],
               subtitle: str, source_note: str) -> list[Path]:
    """题册+答案册两个 PDF。"""
    q_book = html_to_pdf(
        build_book_html(db_title, subtitle, questions, False, source_note),
        BOOKS_DIR / f"{slug}_题册.pdf")
    a_book = html_to_pdf(
        build_book_html(db_title + "·答案册", subtitle, questions, True,
                        source_note),
        BOOKS_DIR / f"{slug}_答案册.pdf")
    return [q_book, a_book]


def build_paper_book(db: Session, paper_id: int) -> list[Path]:
    qs = _load_questions(db, "q.paper_id = :pid", {"pid": paper_id})
    if not qs:
        raise ValueError("试卷无题目")
    meta = db.execute(text("SELECT year, name, source_name, source_url "
                           "FROM papers WHERE id = :pid"),
                      {"pid": paper_id}).first()
    src = (f"来源:{meta.source_name} {meta.source_url} · "
           f"CC BY-SA 4.0(DxAThing/Gaokao-Math-Problems-Compilation)· "
           f"仅供个人教学研究")
    return _make_pair(meta.name, f"paper_{paper_id}", qs,
                      f"{meta.year}年 · 高考数学真题汇编", src)


def build_topic_book(db: Session, tag: str, limit: int = 100) -> list[Path]:
    qs = _load_questions(
        db, ("EXISTS (SELECT 1 FROM json_each(q.knowledge_tags) je "
             "WHERE je.value = :tag) AND p.exam_type = '真题'"),
        {"tag": tag})[:limit]
    if not qs:
        raise ValueError("专题无题目")
    years = f"{qs[0]['year']}-{qs[-1]['year']}"
    src = "来源:GaokaoMathBank 题库(真题) · 仅供个人教学研究"
    return _make_pair(f"高考数学·{tag}专题汇编", f"topic_{tag}", qs,
                      f"{years}年真题 · 按知识点归类", src)


def build_custom_book(db: Session, question_ids: list[int],
                      title: str) -> list[Path]:
    ids = ",".join(str(int(i)) for i in question_ids)
    qs = _load_questions(db, f"q.id IN ({ids})", {})
    if not qs:
        raise ValueError("题单为空")
    order = {qid: i for i, qid in enumerate(question_ids)}
    qs.sort(key=lambda q: order.get(q["id"], 0))
    src = "来源:GaokaoMathBank 自选题单 · 仅供个人教学研究"
    return _make_pair(title or "自选题单", "custom", qs,
                      f"共 {len(qs)} 题 · 自选题单", src)
