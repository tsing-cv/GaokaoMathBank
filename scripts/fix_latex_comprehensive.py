# -*- coding: utf-8 -*-
"""
LaTeX 公式综合修复脚本 v5

修复所有已知的 \frac{ 错误用法模式：

核心问题：\frac{ 在原始数据中被用来表示多种不同的 LaTeX 构造
- 集合：\frac{ CONTENT \right\} → \left\{ CONTENT \right\}
- 向量：\frac{ a } → \vec{a}
- 根号：\frac{ 3 } → \sqrt{3}
- 真分数：\frac{X}{Y} → 保持不变

修复策略：
1. 先修复集合表示（跳过真分数，找到最外层的 \frac{）
2. 再修复真分数（保护起来）
3. 再修复根号 \frac{数字\}
4. 再修复向量 \frac{字母\}
5. 修复其他模式
6. 恢复真分数
"""
import sqlite3
import json
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "mathbank.db"

# 占位符前缀
PH = "___FRAC___"


def fix_set_notation(latex: str) -> str:
    """
    修复集合表示：\frac{ CONTENT \right\} → \left\{ CONTENT \right\}

    策略：从 \right\} 向左扫描，跳过完整的真分数，找到最外层的 \frac{
    """
    if '\\right' not in latex:
        return latex
    # 查找所有 \right\} 或 \right\} 的位置
    right_brace_pattern = re.compile(r'\\right\\?\}')

    # 从右往左处理每个 \right\}
    for m in reversed(list(right_brace_pattern.finditer(latex))):
        right_end = m.end()
        right_start = m.start()

        # 从 \right\} 前面开始向左扫描
        pos = right_start - 1
        frac_pos = -1  # 找到的 \frac{ 位置
        frac_brace_pos = -1  # \frac{ 后面的 { 位置

        while pos >= 0:
            ch = latex[pos]

            if ch == '}':
                # 遇到 }，检查是否是真分数 \frac{...}{...} 的结尾
                # 如果是真分数，跳过整个真分数
                # 向左找匹配的 {
                brace_start = pos - 1
                depth = 1
                while brace_start >= 0 and depth > 0:
                    if latex[brace_start] == '}':
                        depth += 1
                    elif latex[brace_start] == '{':
                        depth -= 1
                    brace_start -= 1
                brace_start += 1  # 回到 { 的位置

                # 检查前面是否是 \frac
                prefix_end = brace_start
                prefix = latex[:prefix_end].rstrip()

                if prefix.endswith('\\frac'):
                    # 这是真分数 \frac{...}{...}，跳过它
                    pos = prefix_end - 5 - 1  # 跳过 \frac
                else:
                    # 不是真分数，继续向左扫描
                    pos -= 1
            elif ch == '{':
                # 遇到单独的 {（不匹配任何 }），检查是否是 \frac{ 或 \left\{
                prefix = latex[:pos].rstrip()

                if prefix.endswith('\\frac'):
                    # 找到最外层的 \frac{
                    frac_pos = pos - 5  # \frac 的长度是 5
                    frac_brace_pos = pos
                    break
                elif prefix.endswith('\\left\\'):
                    # 已经是正确的集合表示 \left\{...\right\}
                    frac_pos = -1
                    break
                else:
                    pos -= 1
            else:
                pos -= 1

        if frac_pos < 0:
            continue

        # 提取集合内容（从 \frac{ 的 { 后面到 \right\} 前面）
        content = latex[frac_brace_pos + 1:right_start]

        # 替换：\frac{ CONTENT \right\} → \left\{ CONTENT \right\}
        latex = latex[:frac_pos] + '\\left\\{' + content + '\\right\\}' + latex[right_end:]

    return latex


def fix_env_notation(latex: str, env: str) -> str:
    """修复矩阵/环境表示：\\frac{env\\} → \\begin{env} 或 \\end{env}

    源数据把 \\begin{cases}/\\end{cases}、\\begin{vmatrix} 等环境定界
    错误写作 \\frac{cases\\}。成对出现时前者为 begin 后者为 end;
    单个出现时按位置判断(开头→begin,结尾→end)。
    """
    marker = f'\\frac{{{env}\\}}'
    if marker not in latex:
        return latex
    parts = latex.split(marker)
    if len(parts) == 3:
        return parts[0] + f'\\begin{{{env}}}' + parts[1] + f'\\end{{{env}}}' + parts[2]
    if len(parts) == 2:
        if latex.startswith(marker):
            return f'\\begin{{{env}}}' + parts[1]
        return parts[0] + f'\\end{{{env}}}'
    # >2 个定界:交替替换(begin,end,begin,end...)
    out = parts[0]
    for i, part in enumerate(parts[1:]):
        out += (f'\\begin{{{env}}}' if i % 2 == 0 else f'\\end{{{env}}}') + part
    return out


def fix_bad_frac_sep(latex: str) -> str:
    r"""\frac{X\}\{Y\} → \frac{X}{Y},线性扫描实现。

    嵌套交替正则((?:[^{}\\]|\\[a-zA-Z]+|\{..\})+?)在长公式上回溯
    爆炸(全库 15608 题跑了 18 分钟未完成),改扫描定位 \}\{ 分隔符,
    向左找 \frac{ 前缀、向右找 \} 结尾,分子/分母要求花括号计数平衡,
    不满足则原样保留(保守放弃,宁漏勿错)。
    """
    if '\\}\\{' not in latex or '\\frac{' not in latex:
        return latex
    out = []
    pos = 0
    while True:
        sep = latex.find('\\}\\{', pos)
        if sep == -1:
            out.append(latex[pos:])
            return ''.join(out)
        # 定位外层 \frac{:从左到右第一个"到 sep 花括号计数平衡"的候选。
        # 分子内嵌的完整真分数(\frac{a}{b})因多出闭合括号天然不平衡,
        # 会被自动跳过;正确外层的内容恰好平衡。
        endm = latex.find('\\}', sep + 4)
        den = latex[sep + 4:endm] if endm != -1 else None
        num, start = None, -1
        if den is not None and den.count('{') == den.count('}'):
            p = latex.find('\\frac{', pos)
            while p != -1 and p < sep:
                n_ = latex[p + 6:sep]
                if n_ and n_.count('{') == n_.count('}'):
                    num, start = n_, p
                    break
                p = latex.find('\\frac{', p + 1)
        # 分子/分母花括号计数平衡才修复,否则保守放弃这一处
        if num is not None:
            out.append(latex[pos:start])
            out.append('\\frac{' + num + '}{' + den + '}')
            pos = endm + 2
        else:
            out.append(latex[pos:sep + 4])
            pos = sep + 4


def fix_latex_fragment(latex: str) -> str:
    """修复单个 LaTeX 片段中的所有错误模式"""
    if not latex or '\\' not in latex:
        return latex

    # ===== 第一步：修复集合表示 =====
    latex = fix_set_notation(latex)

    # ===== 第 1.5 步：修复环境定界(cases/vmatrix/matrix 家族) =====
    # 必须在保护真分数之前——环境定界 \frac{cases\} 会被保护步骤吞掉
    for env in ('cases', 'vmatrix', 'bmatrix', 'pmatrix', 'matrix', 'array'):
        latex = fix_env_notation(latex, env)

    # ===== 第 1.55 步：上下标定界规范化 ^\{X\} → ^{X} =====
    # 源数据把上下标花括号也写成转义形式(r^\{2\}、45^\{\circ\}、
    # a^\{-\frac{3}{2}\}),允许内容一层嵌套;归一后坏分数分隔的
    # 可修范围随之扩大
    latex = re.sub(r'([_^])\\\{((?:[^{}]|\{[^{}]*\})*)\\\}', r'\1{\2}', latex)
    # 闭合为裸 } 的半转义形态(3^\{2}、45^\{\circ}):只归一开头
    latex = re.sub(r'([_^])\\\{', r'\1{', latex)

    # ===== 第 1.6 步：规范化坏分数分隔 \frac{X\}\{Y\} → \frac{X}{Y} =====
    # 必须在保护真分数之前,否则坏形式会被当真分数保护而漏网
    # (这正是此前 3571 处残留的根因);线性扫描实现避免正则回溯爆炸
    latex = fix_bad_frac_sep(latex)

    # ===== 第二步：保护真分数 \frac{X}{Y} =====
    protected_fracs = []
    frac_counter = [0]

    def protect_real_frac(m):
        idx = frac_counter[0]
        frac_counter[0] += 1
        protected_fracs.append(m.group(0))
        return f"{PH}{idx}PH"

    # 匹配真分数：\frac{...}{...}
    latex = re.sub(
        r'\\frac\{((?:[^\\}]|\\(?!\}))+?)\\?\}\\?\{((?:[^\\}]|\\(?!\}))+?)\\?\}',
        protect_real_frac,
        latex
    )

    # ===== 第三步：修复根号 \frac{数字\} → \sqrt{数字} =====
    latex = re.sub(r'\\frac\{([0-9]+(?:\.[0-9]+)?)\\?\}', r'\\sqrt{\1}', latex)

    # 3b. 清理根号修复后可能留下的多余 \}\{ 模式
    # 例如：\frac{\sqrt{3}\}\{2\} → \frac{\sqrt{3}}{2}（外层 \frac{ 已存在）
    latex = re.sub(r'\\frac\{\\sqrt\{([0-9.]+)\}\\?\}\\?\{([0-9.]+)\\?\}',
                   r'\\frac{\\sqrt{\1}}{\2}', latex)
    # 或者没有外层 \frac{ 的情况（使用负向后瞻排除已有 \frac{ 的情况）
    latex = re.sub(r'(?<!\\frac\{)\\sqrt\{([0-9.]+)\}\\?\}\\?\{([0-9.]+)\\?\}',
                   r'\\frac{\\sqrt{\1}}{\2}', latex)

    # 3c. 清理 \frac{X\}\{Y\} 模式（X 和 Y 可能是复杂表达式）
    # 例如：\frac{\frac{\sqrt{3}}{2} → \frac{\sqrt{3}}{2}（去掉多余的 \frac{）
    # 或者：\frac{X\}\{Y\} → \frac{X}{Y}
    latex = re.sub(r'\\frac\{((?:[^\\}]|\\(?!\}))+?)\\?\}\\?\{((?:[^\\}]|\\(?!\}))+?)\\?\}',
                   r'\\frac{\1}{\2}', latex)

    # 3d. 清理双重分数 \frac{\frac{X}{Y} → \frac{X}{Y}
    latex = re.sub(r'\\frac\{\\frac\{((?:[^\\}]|\\(?!\}))+?)\}\{((?:[^\\}]|\\(?!\}))+?)\}',
                   r'\\frac{\1}{\2}', latex)

    # ===== 第四步：修复向量 \frac{字母\} → \vec{字母} =====
    # 带转义右括号 \}
    latex = re.sub(r'\\frac\{([a-z])\\}', r'\\vec{\1}', latex)

    # 不带转义，但后面不跟 { (避免误伤真分数)
    def fix_frac_vector(m):
        letter = m.group(1)
        rest = latex[m.end():]
        if rest.startswith('{'):
            return m.group(0)  # 真分数，保留
        return f'\\vec{{{letter}}}'

    latex = re.sub(r'\\frac\{([a-z])\}', fix_frac_vector, latex)

    # ===== 第五步：修复其他模式 =====


    # 5b. \frac{中文/单位\} → 直接去掉包裹
    def fix_frac_text(m):
        content = m.group(1)
        stripped = content.strip()
        units = ['寸', '尺', '度', '平方寸', '立方尺', '分', '秒', '米', '千米', '克', '千克']
        if stripped in units or re.search(r'[\u4e00-\u9fff]', stripped):
            return content  # 保留原始空格
        return m.group(0)

    latex = re.sub(r'\\frac\{((?:[^\\}]|\\(?!\}))+?)\\?\}', fix_frac_text, latex)

    # 5c. \1{X\}\{Y\} → \frac{X}{Y}
    latex = re.sub(r'\\1\{((?:[^\\}]|\\(?!\}))+?)\\?\}\\?\{((?:[^\\}]|\\(?!\}))+?)\\?\}',
                   r'\\frac{\1}{\2}', latex)

    # 5d. \1{X\} → X
    def fix_backslash1(m):
        content = m.group(1).strip()
        return content

    latex = re.sub(r'\\1\{((?:[^\\}]|\\(?!\}))+?)\\?\}', fix_backslash1, latex)

    # 5e. \frac{ \} → \left\{ \right\} (空集合)
    latex = re.sub(r'\\frac\{\s*\\?\}', r'\\left\\{ \\right\\}', latex)

    # ===== 第六步：恢复真分数 =====
    for idx, frac in enumerate(protected_fracs):
        latex = latex.replace(f"{PH}{idx}PH", frac)

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

    print(f"开始修复 {len(questions)} 道题目...", flush=True)

    for i, q in enumerate(questions):
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
                print(f"  错误 ID {q['id']}: {e}", flush=True)

        # 分批提交:中断也能保住已完成的部分
        if (i + 1) % 2000 == 0:
            conn.commit()
            print(f"  进度 {i+1}/{len(questions)}, 已修复 {fixed_count}", flush=True)

    conn.commit()
    conn.close()

    print(f"\n修复完成！")
    print(f"  修复题目数：{fixed_count}")
    print(f"  错误题目数：{error_count}")


if __name__ == "__main__":
    main()
