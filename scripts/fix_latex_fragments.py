# -*- coding: utf-8 -*-
"""
LaTeX 公式修复脚本 - 修复数据库中的错误 LaTeX 用法

问题模式:
1. \frac{中文/单位\} → 直接去掉 \frac{} 包裹（单位/文本被错误包裹）
2. \frac{vmatrix\} → \begin{vmatrix} 或 \end{vmatrix}
3. \frac{X\}\{Y\} → \frac{X}{Y}（正确分数，但花括号转义有问题）
4. \1{X\}\{Y\} → \frac{X}{Y}（另一种错误分数表示）
5. \1{X\} → X（单独使用时去掉包裹）
"""
import sqlite3
import json
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "mathbank.db"


def fix_latex_fragment(latex: str) -> str:
    """修复单个 LaTeX 片段中的所有错误模式"""
    if not latex or '\\' not in latex:
        return latex

    # 1. 修复 \frac{vmatrix\} → \begin{vmatrix} 或 \end{vmatrix}
    if 'vmatrix' in latex:
        parts = latex.split('\\frac{vmatrix\\}')
        if len(parts) == 3:
            latex = '\\begin{vmatrix}' + parts[1] + '\\end{vmatrix}' + parts[2]
        elif len(parts) == 2:
            if latex.startswith('\\frac{vmatrix\\}'):
                latex = '\\begin{vmatrix}' + parts[1]
            else:
                latex = parts[0] + '\\end{vmatrix}'

    # 2. 修复 \frac{中文/单位\} → 直接去掉包裹（保留原始空格）
    def fix_frac_text(m):
        content = m.group(1)
        stripped = content.strip()
        units = ['寸', '尺', '度', '平方寸', '立方尺', '分', '秒', '米', '千米', '克', '千克']
        if stripped in units or re.search(r'[\u4e00-\u9fff]', stripped):
            return content  # 保留原始空格
        return m.group(0)

    latex = re.sub(r'\\frac\{((?:[^\\}]|\\(?!\}))+?)\\?\}', fix_frac_text, latex)

    # 3. 修复 \frac{X\}\{Y\} → \frac{X}{Y}
    latex = re.sub(r'\\frac\{((?:[^\\}]|\\(?!\}))+?)\\?\}\\?\{((?:[^\\}]|\\(?!\}))+?)\\?\}',
                   r'\\frac{\1}{\2}', latex)

    # 4. 修复 \1{X\}\{Y\} → \frac{X}{Y}
    latex = re.sub(r'\\1\{((?:[^\\}]|\\(?!\}))+?)\\?\}\\?\{((?:[^\\}]|\\(?!\}))+?)\\?\}',
                   r'\\frac{\1}{\2}', latex)

    # 5. 修复 \1{X\} → X（单独使用，如微分符号）
    def fix_backslash1(m):
        content = m.group(1).strip()
        if re.match(r'^[dD][xyz]$', content):
            return content
        return content

    latex = re.sub(r'\\1\{((?:[^\\}]|\\(?!\}))+?)\\?\}', fix_backslash1, latex)

    # 6. 修复 \frac{X\right\} → \left\{X\right\}（集合表示）
    latex = re.sub(r'\\frac\{((?:[^\\}]|\\(?!\}))+?)\\right\\?\}',
                   r'\\left\\{\1\\right\\}', latex)

    # 7. 修复 \frac{ \} → \left\{ \right\}（空集合/填空）
    latex = re.sub(r'\\frac\{\s*\\?\}', r'\\left\\{ \\right\\}', latex)

    return latex


def fix_segments(segments: list) -> list:
    """修复分段数组中的所有 LaTeX 片段"""
    if not segments:
        return segments

    fixed = []
    for seg in segments:
        if seg.get('t') == 'latex' and seg.get('c'):
            original = seg['c']
            fixed_c = fix_latex_fragment(original)
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
