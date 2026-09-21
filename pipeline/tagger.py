"""知识点标注:规则初标(全量) + LLM 精标(仅'待标注'题)。

用法:python -m pipeline.tagger [--llm]
"""
import argparse
import pathlib

import yaml

from app.models import Question, SessionLocal
from app.segments import segments_to_text

K_FILE = pathlib.Path(__file__).parent / "knowledge.yaml"
APIKEY_FILE = pathlib.Path("/Users/mac/Documents/GitHub/APIkey.py")
_with = yaml.safe_load(K_FILE.read_text(encoding="utf-8"))["topics"]
TOPICS = list(_with.keys())


def rule_tag(q: dict) -> list[str]:
    """关键词规则标注(题干+选项全文匹配,1-3个标签)。"""
    body = segments_to_text(q.get("stem") or [])
    for opt in q.get("options") or []:
        body += " " + segments_to_text(opt.get("segs") or [])
    tags = [t for t, kws in _with.items() if any(k in body for k in kws)]
    return tags[:3] or ["待标注"]


def _load_qwen_key() -> str:
    """APIkey.py 是裸注解文件(Qwen: 'sk-...'),exec 后从 __annotations__ 取。"""
    try:
        ns: dict = {}
        exec(APIKEY_FILE.read_text(encoding="utf-8"), ns)
        return ns.get("Qwen") or ns.get("__annotations__", {}).get("Qwen", "")
    except Exception:
        return ""


def llm_tag(questions: list[dict]) -> dict[int, list[str]]:
    """openai 兼容接口批量精标;无 key 或失败返回空。"""
    qwen_key = _load_qwen_key()
    if not qwen_key:
        print("未配置 Qwen key,跳过 LLM 精标")
        return {}
    import httpx
    res: dict[int, list[str]] = {}
    for q in questions:
        body = segments_to_text(q["stem"])[:1500]
        try:
            r = httpx.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={"Authorization": f"Bearer {qwen_key}"},
                json={"model": "qwen-plus",
                      "messages": [
                          {"role": "system", "content":
                           f"给高考数学题打1-3个知识点标签,只能从:{'|'.join(TOPICS)}|待标注 "
                           f"中选,逗号分隔输出,不要任何其他文字。"},
                          {"role": "user", "content": body}],
                      "temperature": 0},
                timeout=30)
            tags = [t.strip() for t in
                    r.json()["choices"][0]["message"]["content"].split(",")
                    if t.strip() and (t.strip() in TOPICS or t.strip() == "待标注")]
            if tags:
                res[q["id"]] = tags
        except Exception as e:
            print(f"LLM 标注失败(id={q['id']}): {e}")
    return res


def tag_all(db, use_llm: bool = False) -> int:
    """全库标注(跳过已有实际标签的题),返回标注数。"""
    n = 0
    pending = []
    for q in db.query(Question).all():
        if q.knowledge_tags and q.knowledge_tags != ["待标注"]:
            continue
        tags = rule_tag({"stem": q.stem, "options": q.options})
        if use_llm and tags == ["待标注"]:
            pending.append(q)
            continue
        if tags != q.knowledge_tags:
            q.knowledge_tags = tags
            n += 1
    db.commit()
    if use_llm and pending:
        print(f"规则无法标注 {len(pending)} 题,交 LLM 精标...")
        got = llm_tag([{"id": q.id, "stem": q.stem, "options": q.options}
                       for q in pending])
        for q in pending:
            if q.id in got:
                q.knowledge_tags = got[q.id]
                n += 1
        db.commit()
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="待标注题交LLM精标")
    a = ap.parse_args()
    with SessionLocal() as db:
        print(f"标注 {tag_all(db, use_llm=a.llm)} 题")
