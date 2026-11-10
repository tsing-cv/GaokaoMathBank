# -*- coding: utf-8 -*-
"""
向量公式修复脚本 - 修复 \frac{a} → \vec{a} 的错误

在向量相关题目中，\frac{a} 被错误地用来表示向量 a，
正确应该是 \vec{a} 或 \mathbf{a}。
"""
import sqlite3
import json
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "mathbank.db"


def fix_vector_latex(latex: str) -> str:
    """修复向量表示：\frac{a} → \vec{a}"""
    if not latex or '\\' not in latex:
        return latex

    # 1. 修复 \frac{a\} → \vec{a}（带转义右括号 \}）
    # 这种模式明确是错误表示，直接转换
    latex = re.sub(r'\\frac\{([a-z])\\}', r'\\vec{\1}', latex)

    # 2. 修复 \frac{a} → \vec{a}（不带转义，但后面不跟 { 分数模式）
    def fix_frac_vector(m):
        letter = m.group(1)
        # 检查后面是否是分数模式 \frac{a}{b}
        rest = latex[m.end():]
        if rest.startswith('{'):
            return m.group(0)  # 这是真分数 \frac{a}{b}，保留
        return f'\\vec{{{letter}}}'

    latex = re.sub(r'\\frac\{([a-z])\}', fix_frac_vector, latex)

    return latex


def fix_segments(segments: list) -> list:
    """修复分段数组中的所有 LaTeX 片段"""
    if not segments:
        return segments

    fixed = []
    for seg in segments:
        if seg.get('t') == 'latex' and seg.get('c'):
            original = seg['c']
            fixed_c = fix_vector_latex(original)
            if fixed_c != original:
                seg = dict(seg)
                seg['c'] = fixed_c
        fixed.append(seg)
    return fixed


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT id, stem, answer, analysis FROM questions')
    questions = cursor.fetchall()

    fixed_count = 0
    error_count = 0

    print(f"开始修复 {len(questions)} 道题目...")

    for q in questions:
        try:
            stem = json.loads(q['stem']) if q['stem'] else []
            answer = json.loads(q['answer']) if q['answer'] else []
            analysis = json.loads(q['analysis']) if q['analysis'] else []

            new_stem = fix_segments(stem)
            new_answer = fix_segments(answer)
            new_analysis = fix_segments(analysis)

            if (new_stem != stem or new_answer != answer or new_analysis != analysis):
                cursor.execute('''
                    UPDATE questions
                    SET stem = ?, answer = ?, analysis = ?
                    WHERE id = ?
                ''', (
                    json.dumps(new_stem, ensure_ascii=False),
                    json.dumps(new_answer, ensure_ascii=False),
                    json.dumps(new_analysis, ensure_ascii=False),
                    q['id']
                ))
                fixed_count += 1

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"  错误 ID {q['id']}: {e}")

    conn.commit()
    conn.close()

    print(f"\n修复完成！")
    print(f"  修复题目数：{fixed_count}")
    print(f"  错误题目数：{error_count}")


if __name__ == "__main__":
    main()
