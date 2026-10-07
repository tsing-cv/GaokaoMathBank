"""采集入口(真题)。

用法:
  python tools/run_collect.py --source github-gaokao-latex [--year 2024] [--limit 3]
  python tools/run_collect.py --source github-gaokaomath [--year 2024]

流程:load_sources → git clone → 逐文件解析 → 图片落盘 → save_paper_payload 入库。
"""
import argparse
import asyncio
import hashlib
import random
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ASSETS_DIR, RAW_DIR  # noqa: E402
from app.models import Paper, Question, SessionLocal  # noqa: E402
from app.segments import segments_to_text  # noqa: E402
from collector.source_registry import load_sources  # noqa: E402

# LaTeX 仓库文件名 → 省份/卷种(中文)。
# 常规形态:<省> / <省>_liberal|_science;历史卷另有 <省>_<文理>_<春|秋>、
# 联考(hei_ji_liao 黑吉辽)、1977 地市初试卷(jiangsu_nanjing_city)等复合形态,
# 缺映射时原样兜底曾把 56 个拼音 key 裸送入库(首页覆盖表 2026-09 暴露),故全量收录。
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
    "syllabus": "大纲卷", "syllabus_paper_1": "大纲I卷",
    "syllabus_paper_2": "大纲II卷", "new_curriculum_paper_1": "新课标I卷",
    "new_curriculum_paper_2": "新课标II卷", "sichuan_ordinary": "四川",
    "sichuan_postponed": "四川延考",
    # ---- 历史卷复合形态(1952-2005 与 1977 各省自命题) ----
    "national": "全国", "national_paper_4": "全国IV卷",
    "beijing_liberal_autumn": "北京", "beijing_science_autumn": "北京",
    "beijing_liberal_spring": "北京", "beijing_science_spring": "北京",
    "anhui_liberal_spring": "安徽", "anhui_science_spring": "安徽",
    "gansu": "甘肃", "guizhou": "贵州", "hebei": "河北", "henan": "河南",
    "heilongjiang": "黑龙江", "heilongjiang_preliminary": "黑龙江",
    "jilin": "吉林", "ningxia": "宁夏", "qinghai": "青海",
    "shandong_a": "山东", "shandong_b": "山东", "shanxi": "山西",
    "tibet": "西藏", "xinjiang": "新疆", "yunnan": "云南",
    "inner_mongolia": "内蒙古",
    "guangdong_hainan_included": "广东", "guangxi_baise": "广西",
    "hunan_zhuzhou_pilot": "湖南",
    # 联考卷(组合名与库内既有"三南"同风格,全称见卷名)
    "hei_ji_liao": "黑吉辽", "hu_min": "沪闽", "henan_guangdong": "豫粤",
    "jing_hui": "京皖", "jing_meng_wan": "京蒙皖",
    "jing_xiang_e_yun_qiong_gui": "京湘鄂云琼贵", "sannan": "三南",
    "yue_gui": "粤桂", "yue_yu_su_gui": "苏豫粤桂",
    # 1977 江苏各市/地区初试卷(卷名含地市全称)
    "jiangsu_changzhou_city": "江苏", "jiangsu_huaiyin_region": "江苏",
    "jiangsu_lianyungang_city": "江苏", "jiangsu_nanjing_city": "江苏",
    "jiangsu_nantong": "江苏", "jiangsu_nantong_city": "江苏",
    "jiangsu_nantong_region": "江苏", "jiangsu_state_farm_system": "江苏",
    "jiangsu_suzhou_city": "江苏", "jiangsu_suzhou_region": "江苏",
    "jiangsu_wuxi_city": "江苏", "jiangsu_xuzhou_city_region": "江苏",
    "jiangsu_yancheng_region": "江苏", "jiangsu_yangzhou_region": "江苏",
    "jiangsu_zhenjiang_region": "江苏",
    "unknown": "其他",
}


def meta_from_tex_filename(year: int, fname: str) -> dict:
    """content/<年>/<名>.tex → meta。名 = <卷种key>[_liberal|_science][...]。

    文理标记取自文件名任意位置的 liberal/science 段(历史卷存在
    <省>_liberal_spring 这类"标记在中间"的形态,只看尾缀会漏)。
    """
    stem = fname.rsplit(".", 1)[0]
    parts = stem.split("_")
    subject = "文理同卷"
    if "liberal" in parts:
        subject = "文科"
    elif "science" in parts:
        subject = "理科"
    # 查表链:完整形态 → 剥掉文理/春秋修饰段(中间或尾部的都剥)
    stripped = "_".join(p for p in parts
                        if p not in ("liberal", "science", "spring", "autumn"))
    province = _TEX_PROVINCE.get(stem) or _TEX_PROVINCE.get(stripped, stripped)
    if province.startswith("新高考"):
        subject = "新高考"
    return {"year": year, "province": province, "exam_type": "真题",
            "subject": subject, "name": f"{year}年{province}数学"}


# gaokaomath 文件名卷种 → 库内 tex 源同款中文(罗马数字/甲乙卷)
_PDF_PROVINCE = {
    "全国1": "全国I卷", "全国2": "全国II卷", "全国3": "全国III卷",
    "全国4": "全国IV卷", "全国甲": "全国甲卷", "全国乙": "全国乙卷",
    "全国": "全国甲卷",  # 2024 起"全国文/理"即甲卷分文理
    "新高考1": "新高考I卷", "新高考2": "新高考II卷",
    "大纲1": "大纲I卷", "大纲2": "大纲II卷", "大纲": "大纲卷",
    "新课标": "新课标卷", "全国新课程": "新课标卷",
    "新课标1": "新课标I卷", "新课标2": "新课标II卷",
}


def meta_from_pdf_filename(fname: str) -> dict:
    """gaokaomath PDF:(春季)+年份+卷种(+文理)(+适用省份).pdf → meta。

    卷种归一到 _TEX_PROVINCE 同款中文(全国1→全国I卷、全国文→全国甲卷),
    使附件能按(年,卷种,文理)回填到 tex 源已建的卷。
    """
    stem = fname.rsplit(".", 1)[0]
    spring = stem.startswith("春季")
    if spring:
        stem = stem[2:]
    m = re.match(r"(\d{4})(.*)", stem)
    if not m:
        return {"year": 0, "province": fname, "exam_type": "真题",
                "subject": "文理同卷", "name": fname}
    year, rest = int(m.group(1)), m.group(2)
    if rest.startswith("春季"):  # "2013春季上海" 前缀风格
        spring = True
        rest = rest[2:]
    elif rest.endswith("春季"):  # "2026上海春季" 后缀风格
        spring = True
        rest = rest[:-2]
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
    province = _PDF_PROVINCE.get(rest, rest) or "全国"  # 纯年份文件兜底
    # 省份卷(北京/上海…)name 带"卷"字,卷种(全国I卷…)自带
    disp = province if province.endswith("卷") else f"{province}卷"
    name = f"{year}年{disp}"
    if subject in ("文科", "理科"):
        name += f"（{subject[0]}）"
    if spring:
        name += "(春)"  # 与 tex 源 \chapter 同款省写
        province += "(春季)"
    return {"year": year, "province": province, "exam_type": "真题",
            "subject": subject, "name": name, "_provs": provs}


def q_hash(stem_segs) -> str:
    """题目去重指纹:规范化题干纯文本的 md5。"""
    txt = re.sub(r"\s+", "", segments_to_text(stem_segs))
    return hashlib.md5(txt.encode()).hexdigest()


def save_paper_payload(db, payload: dict) -> Paper:
    """按(年份,省份,类型,名称)卷级去重;题目按 source_hash 去重。

    已存在的卷若本次带 pdf_path 且原先为空(附件源登记),回填附件路径。
    """
    paper = db.query(Paper).filter_by(
        year=payload["year"], province=payload["province"],
        exam_type=payload["exam_type"], name=payload["name"]).first()
    if not paper and not payload.get("questions"):
        # 二级匹配:仅附件登记(payload 无题目)时启用。\chapter name 与
        # 附件侧构造的 name 措辞可能差一字,按(年,卷种,文理)仍能对上
        # 同一卷。带题采集禁用:模拟题同年同省同科别有多套卷
        # (如 2018通用(一)~(十五)),二级匹配会把后续卷吸进第一套
        # 并丢弃其题目(2026-09-22 eol 采集实测教训)。
        paper = db.query(Paper).filter_by(
            year=payload["year"], province=payload["province"],
            exam_type=payload["exam_type"],
            subject=payload["subject"]).first()
    if paper:
        if payload.get("pdf_path") and not paper.pdf_path:
            paper.pdf_path = payload["pdf_path"]
            db.commit()
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
        # 图片流题 stem 均为 [图],默认指纹相同 → 允许 payload 显式覆盖
        h = q.get("source_hash") or q_hash(q["stem"])
        if db.query(Question).filter_by(source_hash=h).first():
            continue  # 题目级去重(跨卷转载)
        db.add(Question(
            paper_id=paper.id, seq=q["seq"], qtype=q["qtype"],
            stem=q["stem"], options=q.get("options", []),
            answer=q.get("answer", []), analysis=q.get("analysis", []),
            knowledge_tags=[], source_hash=h))
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
    from app import RAW_DIR

    src = next(s for s in load_sources() if s["name"] == source_name)

    if source_name == "eol-shiti":  # html_site 源,不走 git clone
        await _collect_eol_shiti(src, limit)
        return

    from collector.fetchers.gitc import GitFetcher
    from collector.ingesters.latex_archive import parse_tex

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
        # 原卷附件库:普通高考/<年>/*.pdf + 春季高考/<年>/*.pdf →
        # 回填 tex 源已建卷的 pdf_path;目录偶有错置文件(2007/ 下藏
        # 2002 卷),按文件名年份过滤而非目录名
        files = sorted((repo / "普通高考").glob("*/*.pdf"))
        files += sorted((repo / "春季高考").glob("*/*.pdf"))
        metas = [(f, meta_from_pdf_filename(f.name)) for f in files]

        def _year_ok(y: int) -> bool:
            if year:
                return y == year
            if not y:
                return True
            if min_year is not None and y < min_year:
                return False
            if max_year is not None and y > max_year:
                return False
            return True

        metas = [(f, m) for f, m in metas if _year_ok(m["year"])]
        if limit:
            metas = metas[:limit]
        with SessionLocal() as db:
            for f, meta in metas:
                meta["source_name"] = src["name"]
                meta["source_url"] = src["entry"]
                meta["pdf_path"] = str(f.resolve())
                payload = {**meta, "questions": []}
                p = save_paper_payload(db, payload)
                print(f"登记原卷: {p.name}")


async def _collect_eol_shiti(src: dict, limit: int | None) -> None:
    """eol"数学模拟"频道:静态列表 + 图片流详情(2026-09 实测无需无头浏览器)。

    每套模拟卷 = 一串正文图片(./W0*.jpg),逐图入库为"图片题";
    频控:页面间 1-3s、图片间 0.5-1.5s,串行(≤3 并发约束)。
    """
    import httpx

    from collector.fetchers.base import UA
    from collector.fetchers.html import HtmlFetcher
    from collector.ingesters.eol_mock import (
        meta_from_title, paginated_urls, parse_list_page, parse_paper_page)

    base = src["entry"]
    fetcher = HtmlFetcher()
    items = parse_list_page(await fetcher.fetch_page(base))
    if limit:
        items = items[:limit]
    out_dir = ASSETS_DIR / "eol"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"列表获取: {len(items)} 套模拟卷")
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=30,
                                 follow_redirects=True) as cli:
        for rel, title in items:
            meta = meta_from_title(title)
            detail = urljoin(base, rel)
            with SessionLocal() as db:  # 幂等:已入库卷直接跳过
                if db.query(Paper).filter_by(
                        year=meta["year"], province=meta["province"],
                        exam_type=meta["exam_type"],
                        name=meta["name"]).first():
                    print(f"已存在,跳过: {title}")
                    continue
            first = parse_paper_page(await fetcher.fetch_page(detail))
            img_rels = list(first["images"])
            for pu in paginated_urls(detail, first["pages"])[1:]:
                await asyncio.sleep(random.uniform(1, 3))
                img_rels += parse_paper_page(
                    await fetcher.fetch_page(pu))["images"]
            stem_base = detail.rsplit("/", 1)[1].rsplit(".", 1)[0]
            questions = []
            for n, rel_img in enumerate(img_rels, 1):
                absu = urljoin(detail, rel_img)
                fname = f"{stem_base}_{n:02d}{Path(rel_img).suffix}"
                dst = out_dir / fname
                if not dst.exists():
                    for attempt in range(3):  # 单图重试,失败跳过不中断
                        try:
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                            r = await cli.get(absu)
                            r.raise_for_status()
                            dst.write_bytes(r.content)
                            break
                        except Exception as e:
                            if attempt == 2:
                                print(f"  图片失败跳过: {absu} ({e})")
                if not dst.exists():
                    continue
                questions.append({
                    "seq": len(questions) + 1, "qtype": "图片",
                    "stem": [{"t": "img", "c": f"/assets/eol/{fname}"}],
                    "options": [], "answer": [], "analysis": [],
                    "source_hash": hashlib.md5(absu.encode()).hexdigest()})
            payload = {**meta, "source_name": src["name"],
                       "source_url": detail, "questions": questions}
            with SessionLocal() as db:
                p = save_paper_payload(db, payload)
            print(f"入库: {p.name} [{p.question_count}图]")


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
