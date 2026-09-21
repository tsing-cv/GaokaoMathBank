"""采集入口(真题)。

用法:
  python tools/run_collect.py --source github-gaokao-latex [--year 2024] [--limit 3]
  python tools/run_collect.py --source github-gaokaomath [--year 2024]

流程:load_sources → git clone → 逐文件解析 → 图片落盘 → save_paper_payload 入库。
"""
import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ASSETS_DIR, RAW_DIR  # noqa: E402
from app.models import Paper, Question, SessionLocal  # noqa: E402
from app.segments import segments_to_text  # noqa: E402
from collector.source_registry import load_sources  # noqa: E402

# LaTeX 仓库文件名 → (省份/卷种, subject)
_TEX_PROVINCE = {
    "beijing": "北京", "shanghai": "上海", "shanghai_spring": "上海(春季)",
    "tianjin": "天津", "zhejiang": "浙江", "jiangsu": "江苏",
    "anhui": "安徽", "shaanxi": "陕西", "sichuan": "四川", "shandong": "山东",
    "jiangxi": "江西", "liaoning": "辽宁", "fujian": "福建", "guangdong": "广东",
    "hubei": "湖北", "hunan": "湖南", "chongqing": "重庆", "guangxi": "广西",
    "national_paper_1": "全国I卷", "national_paper_2": "全国II卷",
    "national_paper_3": "全国III卷", "national_paper_a": "全国甲卷",
    "national_paper_b": "全国乙卷", "new_curriculum": "新课标卷",
    "new_gaokao_paper_1": "新高考I卷", "new_gaokao_paper_2": "新高考II卷",
}
_TEX_SUBJECT = {"liberal": "文科", "science": "理科"}


def meta_from_tex_filename(year: int, fname: str) -> dict:
    """content/<年>/<名>.tex → meta。名 = <卷种key>[_liberal|_science]。"""
    stem = fname.rsplit(".", 1)[0]
    subject = "文理同卷"
    if stem.endswith("_liberal"):
        subject, stem = "文科", stem[:-len("_liberal")]
    elif stem.endswith("_science"):
        subject, stem = "理科", stem[:-len("_science")]
    province = _TEX_PROVINCE.get(stem, stem)
    if province.startswith("新高考"):
        subject = "新高考"
    return {"year": year, "province": province, "exam_type": "真题",
            "subject": subject, "name": f"{year}年{province}数学"}


def meta_from_pdf_filename(fname: str) -> dict:
    """gaokaomath PDF:年份+卷种(+文理)(+适用省份).pdf → meta。"""
    stem = fname.rsplit(".", 1)[0]
    spring = stem.startswith("春季")
    if spring:
        stem = stem[2:]
    m = re.match(r"(\d{4})(.*)", stem)
    if not m:
        return {"year": 0, "province": fname, "exam_type": "真题",
                "subject": "文理同卷", "name": fname}
    year, rest = int(m.group(1)), m.group(2)
    provs = ""
    if "(" in rest:
        rest, provs = rest.split("(", 1)
        provs = provs.rstrip(")")
    subject = "文理同卷"
    if rest.endswith("文"):
        subject, rest = "文科", rest[:-1]
    elif rest.endswith("理"):
        subject, rest = "理科", rest[:-1]
    if rest.startswith("新高考"):
        subject = "新高考"
    province = rest or "全国"
    name = f"{year}年{province}数学" + ("(春季)" if spring else "")
    province = (province + "(春季)") if spring else province
    return {"year": year, "province": province, "exam_type": "真题",
            "subject": subject, "name": name, "_provs": provs}


def q_hash(stem_segs) -> str:
    """题目去重指纹:规范化题干纯文本的 md5。"""
    txt = re.sub(r"\s+", "", segments_to_text(stem_segs))
    return hashlib.md5(txt.encode()).hexdigest()


def save_paper_payload(db, payload: dict) -> Paper:
    """按(年份,省份,类型,名称)卷级去重;题目按 source_hash 去重。"""
    paper = db.query(Paper).filter_by(
        year=payload["year"], province=payload["province"],
        exam_type=payload["exam_type"], name=payload["name"]).first()
    if paper:
        return paper
    paper = Paper(
        year=payload["year"], province=payload["province"],
        exam_type=payload["exam_type"], subject=payload["subject"],
        name=payload["name"], source_name=payload.get("source_name", ""),
        source_url=payload.get("source_url", ""),
        pdf_path=payload.get("pdf_path", ""), status="parsed",
        question_count=len(payload.get("questions", [])))
    db.add(paper)
    db.commit()
    db.refresh(paper)
    for q in payload.get("questions", []):
        if db.query(Question).filter_by(source_hash=q_hash(q["stem"])).first():
            continue  # 题目级去重(跨卷转载)
        db.add(Question(
            paper_id=paper.id, seq=q["seq"], qtype=q["qtype"],
            stem=q["stem"], options=q.get("options", []),
            answer=q.get("answer", []), analysis=q.get("analysis", []),
            knowledge_tags=[], source_hash=q_hash(q["stem"])))
    db.commit()
    return paper


def _relocate_images(payload: dict, repo_dir: Path) -> dict:
    """把 img 段的仓库相对路径替换为 /assets/... 并复制文件。"""
    mapping: dict[str, str] = {}
    prefix = f"{payload['year']}_{''.join(p for p in payload['province'] if p not in '()/')}"
    for rel in payload.pop("_images", []):
        src = repo_dir / rel
        if not src.exists():
            continue
        new_name = f"{prefix}_{src.name}"
        dst = ASSETS_DIR / new_name
        if not dst.exists():
            shutil.copy(src, dst)
        mapping[rel] = f"/assets/{new_name}"

    def fix(segs):
        for s in segs:
            if s["t"] == "img" and s["c"] in mapping:
                s["c"] = mapping[s["c"]]

    for q in payload.get("questions", []):
        fix(q["stem"])
        fix(q["answer"])
        fix(q["analysis"])
        for o in q.get("options", []):
            fix(o.get("segs", []))
    return payload


async def run(source_name: str, year: int | None, limit: int | None,
              min_year: int | None = None, max_year: int | None = None) -> None:
    from collector.fetchers.gitc import GitFetcher
    from collector.ingesters.latex_archive import parse_tex
    from app import RAW_DIR

    src = next(s for s in load_sources() if s["name"] == source_name)
    repo = await GitFetcher().fetch(src["entry"], RAW_DIR / source_name)

    def _in_range(f: Path) -> bool:
        if year:
            return f.parent.name == str(year)
        y = int(f.parent.name) if f.parent.name.isdigit() else 0
        if min_year is not None and y and y < min_year:
            return False
        if max_year is not None and y and y > max_year:
            return False
        return True

    if source_name == "github-gaokao-latex":
        # 结构化:content/<年>/*.tex
        files = sorted((repo / "content").glob("*/*.tex"))
        files = [f for f in files if _in_range(f)]
        if limit:
            files = files[:limit]
        with SessionLocal() as db:
            for f in files:
                meta = meta_from_tex_filename(int(f.parent.name), f.name)
                payload = parse_tex(f.read_text(encoding="utf-8"), meta)
                payload["source_name"] = src["name"]
                payload["source_url"] = f"{src['entry']}/blob/main/content/{f.parent.name}/{f.name}"
                _relocate_images(payload, repo)
                p = save_paper_payload(db, payload)
                print(f"入库: {p.name} [{p.subject}] {p.question_count}题")
    elif source_name == "github-gaokaomath":
        # 原卷附件库:普通高考/<年>/*.pdf → 仅建 Paper 记录
        files = sorted((repo / "普通高考").glob("*/*.pdf"))
        files = [f for f in files if _in_range(f)]
        if limit:
            files = files[:limit]
        with SessionLocal() as db:
            for f in files:
                meta = meta_from_pdf_filename(f.name)
                meta["source_name"] = src["name"]
                meta["source_url"] = src["entry"]
                meta["pdf_path"] = str(f)
                payload = {**meta, "questions": []}
                p = save_paper_payload(db, payload)
                print(f"登记原卷: {p.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="真题采集入库")
    ap.add_argument("--source", required=True, help="sources.yaml 中的来源名")
    ap.add_argument("--year", type=int, default=None, help="只处理某年")
    ap.add_argument("--limit", type=int, default=None, help="限量(调试)")
    ap.add_argument("--min-year", type=int, default=None,
                    help="年份下限(含),如 2006")
    ap.add_argument("--max-year", type=int, default=None,
                    help="年份上限(含),如 2026")
    a = ap.parse_args()
    import asyncio
    asyncio.run(run(a.source, a.year, a.limit, a.min_year, a.max_year))
