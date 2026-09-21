"""PDF/文本试卷 → 结构化题目。

策略:pdfplumber 提取整卷文本 → 行级去噪 → 分离参考答案段 →
行首题号切分 → 小节标题推进题型 → 选项拆分 → 答案关联。
公式保持 $...$ 进入分段JSON(由 app.segments.parse_segments 处理)。
"""
import re
from pathlib import Path

import pdfplumber

from app.segments import parse_segments

# 行首题号:1. / 1、/ 1.
_QNO = re.compile(r"^\s*(\d{1,2})[.、.]\s*", re.M)
# 选项:A. xxx / A、xxx(选项字母后跟点或顿号)
_OPT = re.compile(r"([A-D])[.、.]\s*")
# 噪音行(水印/广告/联系方式/网址/页脚)
_NOISE = re.compile(
    r"(广告|招租|QQ|微信|扫码|关注|订阅|www\.|http|来源[:：]|第\s*\d+\s*页|"
    r"版权|下载|更多资料|客服|咨询电话)", re.I)
# 小节标题与题型
_SEC_CHOICE = re.compile(r"选择题")
_SEC_FILL = re.compile(r"填空题")
_SEC_SOLVE = re.compile(r"解答题|解答")


def _clean_lines(text: str) -> list[str]:
    """去空行与噪音行。"""
    return [ln.strip() for ln in text.splitlines()
            if ln.strip() and not _NOISE.search(ln)]


def _detect_type(context_before: str, seg_text: str, cur_type: str) -> str:
    """题型 = 小节标题推进的当前类型;题干含≥3个选项字母则为选择题。"""
    opts = _OPT.findall(seg_text)
    if len(opts) >= 3:
        return "选择"
    return cur_type


def _split_options(seg_text: str) -> tuple[str, list[dict]]:
    """拆出题干与选项列表。"""
    parts = _OPT.split(seg_text)
    stem_text = parts[0]
    options = []
    # split 产生 [题干, 'A', A内容, 'B', B内容, ...]
    for j in range(1, len(parts) - 1, 2):
        content = parts[j + 1].strip()
        # 截断选项内容到下一个选项前的空白噪音
        options.append({"label": parts[j], "segs": parse_segments(content)})
    return stem_text, options


def _find_answer(seq: int, ans_part: str) -> list[dict]:
    """从参考答案段提取该题答案(容忍 '1.A'、'13.√5'、'17.y=-2' 等格式)。"""
    m = re.search(
        rf"(?:^|\s){seq}[.、.]\s*(.+?)(?=(?:\s+\d{{1,2}}[.、.])|$)",
        ans_part, re.S)
    if not m:
        return []
    return parse_segments(m.group(1).strip())


def parse_paper_text(text: str, meta: dict) -> dict:
    """整卷文本 → {**meta, questions: [...]}。"""
    lines = _clean_lines(text)
    joined = "\n".join(lines)

    # 分离参考答案段
    ans_part, body = "", joined
    m_ans = re.search(r"^参考答案\s*$", joined, re.M)
    if m_ans:
        body, ans_part = joined[:m_ans.start()], joined[m_ans.end():]

    questions: list[dict] = []
    cur_type = "解答"
    matches = list(_QNO.finditer(body))
    for i, m in enumerate(matches):
        seg_text = body[m.end():matches[i + 1].start() if i + 1 < len(matches) else len(body)]
        # 小节标题推进当前题型(看题号前的上下文窗口)
        context = body[max(0, m.start() - 80):m.start()]
        if _SEC_FILL.search(context) and not _SEC_CHOICE.search(context):
            cur_type = "填空"
        elif _SEC_SOLVE.search(context) and not (_SEC_CHOICE.search(context) or _SEC_FILL.search(context)):
            cur_type = "解答"
        elif _SEC_CHOICE.search(context):
            cur_type = "选择"

        qtype = _detect_type(context, seg_text, cur_type)
        stem_text, options = (("", []))
        if qtype == "选择":
            stem_text, options = _split_options(seg_text)
        else:
            stem_text = seg_text

        questions.append({
            "seq": int(m.group(1)),
            "qtype": qtype,
            "stem": parse_segments(stem_text.strip().rstrip("。")),
            "options": options,
            "answer": _find_answer(int(m.group(1)), ans_part),
            "analysis": [],
        })

    return {**meta, "questions": questions,
            "question_count": len(questions)}


def ingest_pdf(pdf_path: Path, meta: dict) -> dict:
    """PDF → 文本 → 结构化。"""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    return parse_paper_text(text, meta)
