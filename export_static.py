# -*- coding: utf-8 -*-
"""
导出题库数据为 JSON，用于静态页面展示
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "mathbank.db"
OUTPUT_DIR = Path(__file__).parent / "static" / "data"


def export_papers():
    """导出试卷列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, year, province, exam_type, subject, name, question_count
        FROM papers
        WHERE question_count > 0
        ORDER BY year DESC, province
    """)
    papers = []
    for row in cursor.fetchall():
        papers.append({
            "id": row[0],
            "year": row[1],
            "province": row[2] or "",
            "exam_type": row[3] or "",
            "subject": row[4] or "",
            "name": row[5] or "",
            "question_count": row[6] or 0
        })
    conn.close()
    return papers


def export_questions():
    """导出题目（精简版，不含解析）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.id, q.paper_id, q.seq, q.qtype, q.stem, q.answer,
               q.knowledge_tags, q.difficulty,
               p.year, p.province, p.exam_type, p.name as paper_name
        FROM questions q
        JOIN papers p ON q.paper_id = p.id
        ORDER BY p.year DESC, q.seq
    """)
    questions = []
    for row in cursor.fetchall():
        stem = json.loads(row[4]) if row[4] else []
        answer = json.loads(row[5]) if row[5] else []
        tags = json.loads(row[6]) if row[6] else []

        # 提取 stem 中的文本（用于搜索）
        stem_text = " ".join([item.get("c", "") for item in stem if item.get("t") == "text"])

        questions.append({
            "id": row[0],
            "paper_id": row[1],
            "seq": row[2],
            "qtype": row[3] or "",
            "stem": stem,
            "answer": answer,
            "knowledge_tags": tags,
            "difficulty": row[7],
            "year": row[8],
            "province": row[9] or "",
            "exam_type": row[10] or "",
            "paper_name": row[11] or "",
            "stem_text": stem_text  # 用于搜索
        })
    conn.close()
    return questions


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("导出试卷列表...")
    papers = export_papers()
    papers_path = OUTPUT_DIR / "papers.json"
    with open(papers_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {len(papers)} 套试卷 → {papers_path}")

    print("导出题目数据...")
    questions = export_questions()
    questions_path = OUTPUT_DIR / "questions.json"
    with open(questions_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {len(questions)} 道题目 → {questions_path}")

    # 生成统计信息
    stats = {
        "total_papers": len(papers),
        "total_questions": len(questions),
        "years": sorted(set(q["year"] for q in questions if q["year"]), reverse=True),
        "provinces": sorted(set(q["province"] for q in questions if q["province"])),
        "exam_types": sorted(set(q["exam_type"] for q in questions if q["exam_type"])),
        "qtypes": sorted(set(q["qtype"] for q in questions if q["qtype"]))
    }
    stats_path = OUTPUT_DIR / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 统计信息 → {stats_path}")

    print("\n导出完成！")


if __name__ == "__main__":
    main()
