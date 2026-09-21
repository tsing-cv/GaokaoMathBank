"""题库覆盖报表:总量/年份/卷种/知识点/答案解析覆盖率。

用法:python tools/stats.py [--md]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.models import SessionLocal  # noqa: E402


def build_report(db) -> str:
    q = lambda sql, **p: db.execute(text(sql), p).all()  # noqa: E731
    papers, questions = (q("SELECT COUNT(*) FROM papers")[0][0],
                         q("SELECT COUNT(*) FROM questions")[0][0])
    with_ans = q("SELECT COUNT(*) FROM questions "
                 "WHERE json_type(answer) != 'null' AND length(answer) > 2")[0][0]
    with_ana = q("SELECT COUNT(*) FROM questions "
                 "WHERE json_type(analysis) != 'null' AND length(analysis) > 2")[0][0]
    year_rows = q("SELECT p.year, COUNT(DISTINCT p.id), COUNT(q.id) "
                  "FROM papers p LEFT JOIN questions q ON q.paper_id = p.id "
                  "GROUP BY p.year ORDER BY p.year")
    prov_rows = q("SELECT province, COUNT(*) FROM papers GROUP BY province "
                  "ORDER BY COUNT(*) DESC")
    tag_rows = q("SELECT je.value AS t, COUNT(*) FROM questions q, "
                 "json_each(q.knowledge_tags) je GROUP BY je.value "
                 "ORDER BY COUNT(*) DESC")
    untaged = q("SELECT COUNT(*) FROM questions q WHERE EXISTS ("
                "SELECT 1 FROM json_each(q.knowledge_tags) je "
                "WHERE je.value = '待标注')")[0][0]
    no_ans = questions - with_ans

    L = ["# GaokaoMathBank 覆盖报表", "",
         f"- 试卷:**{papers}** 卷(真题)  题目:**{questions}** 题",
         f"- 带答案:**{with_ans}**({with_ans * 100 // questions}%)  "
         f"带解析:**{with_ana}**({with_ana * 100 // questions}%)  "
         f"缺答案:{no_ans} 题",
         f"- 待标注(LLM 精标预留):**{untaged}** 题", "",
         "## 年份覆盖", "", "| 年份 | 卷数 | 题数 |", "|---|---|---|"]
    L += [f"| {y} | {pc} | {qc} |" for y, pc, qc in year_rows]
    L += ["", f"共 {len(prov_rows)} 个卷种:" +
          "、".join(f"{p}({c})" for p, c in prov_rows)]
    L += ["", "## 知识点分布", "", "| 知识点 | 题数 |", "|---|---|"]
    L += [f"| {t} | {n} |" for t, n in tag_rows]
    return "\n".join(L)


if __name__ == "__main__":
    with SessionLocal() as db:
        rep = build_report(db)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--md" else None
    if out:
        out.write_text(rep, encoding="utf-8")
        print(f"written: {out}")
    else:
        print(rep)
