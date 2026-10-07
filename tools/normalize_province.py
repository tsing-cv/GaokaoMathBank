"""历史库 province 规范化迁移(2026-09:首页覆盖表暴露拼音/空值)。

修复三类历史遗留:
1. 拼音 province(beijing_liberal_autumn 等 56 个 key)→ 中文;
2. 空 province(github-gaokaomath 纯年份附件卷,如 name="1952年卷")→ 全国,
   name 规范为 "1952年全国卷"(与采集端 meta_from_pdf_filename 兜底一致,
   重采可按一级键去重);
3. 同 (年,卷种,类型,文理) 下无题附件卷并入有题卷(回填 pdf_path 后删除),
   消除首页同年"全国卷/年卷"双行;
顺带:subject=文理同卷但卷名带（文）/（理）→ 修正科别。

用法:
  python tools/normalize_province.py            # dry-run,只打印计划
  python tools/normalize_province.py --apply    # 执行迁移
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Paper, Question, SessionLocal  # noqa: E402
from tools.run_collect import _TEX_PROVINCE  # noqa: E402

# 空 province 的纯年份卷名 → 规范全国卷名("1979年卷（文）"→"1979年全国卷（文）")
_BARE_NAME = re.compile(r"^(\d{4})年卷(.*)$")
# 卷名尾注(文)/(理)/(春文)/(秋理)… → 科别
_NAME_SUBJ = re.compile(r"[（(](?:春|秋)?([文理])[)）]$")

# 文理/春秋修饰段(查表前剥掉,与采集端 meta_from_tex_filename 同链)
_MODIFIER = ("liberal", "science", "spring", "autumn")


def _to_chinese(prov: str) -> str | None:
    """拼音 province → 中文:精确命中,或剥掉文理/春秋修饰段后命中。"""
    if prov in _TEX_PROVINCE:
        return _TEX_PROVINCE[prov]
    stripped = "_".join(p for p in prov.split("_") if p not in _MODIFIER)
    return _TEX_PROVINCE.get(stripped)


def normalize_provinces(db) -> dict:
    """执行规范化,返回统计。幂等:已是中文且无重复合并时全为 0。"""
    stats = {"updated": 0, "merged": 0, "subject_fixed": 0}
    papers = db.query(Paper).all()
    for p in papers:
        changed = False
        # 1) 拼音 → 中文(与采集端共用同一张映射表,防两处漂移)
        if p.province and re.fullmatch(r"[a-z0-9_]+", p.province):
            cn = _to_chinese(p.province)
            if cn:
                p.province = cn
                changed = True
        # 2) 空 province → 全国;纯年份卷名规范化
        elif not p.province:
            p.province = "全国"
            m = _BARE_NAME.match(p.name or "")
            if m:
                p.name = f"{m.group(1)}年全国卷{m.group(2)}"
            changed = True
        # 3) 科别按卷名尾注修正(仅"文理同卷"且可判定时)
        m = _NAME_SUBJ.search(p.name or "")
        if p.subject == "文理同卷" and m:
            p.subject = "文科" if m.group(1) == "文" else "理科"
            stats["subject_fixed"] += 1
        if changed:
            stats["updated"] += 1
    db.commit()

    # 4) 无题附件卷并入同键有题卷
    groups: dict[tuple, list[Paper]] = {}
    for p in db.query(Paper).all():
        groups.setdefault(
            (p.year, p.province, p.exam_type, p.subject), []).append(p)
    for key, ps in groups.items():
        bare = [p for p in ps if p.question_count == 0 and p.pdf_path]
        rich = [p for p in ps if p.question_count > 0]
        if not bare or not rich:
            continue  # 组内没有"有题卷"时不合并,保留附件卷
        for b in bare:
            n_q = db.query(Question).filter_by(paper_id=b.id).count()
            if n_q:  # 安全阀:实际挂着题目的卷绝不删
                continue
            for r in rich:
                if not r.pdf_path:
                    r.pdf_path = b.pdf_path
                    print(f"合并: {b.name}(附件) → {r.name} 回填 pdf")
                    break
            else:
                print(f"合并: {b.name}(附件) → {rich[0].name}(已有pdf,仅去重)")
            db.delete(b)
            stats["merged"] += 1
    db.commit()
    return stats


def _plan(db) -> None:
    """dry-run:打印将要发生的变更,不动库。"""
    n_pinyin = db.query(Paper).filter(
        Paper.province.regexp_match(r"[a-z0-9_]+")).count() \
        if hasattr(Paper.province, "regexp_match") else -1
    rows = db.query(Paper).all()
    pinyin = [p for p in rows
              if p.province and re.fullmatch(r"[a-z0-9_]+", p.province)]
    empty = [p for p in rows if not p.province]
    subjfix = [p for p in rows if p.subject == "文理同卷"
               and _NAME_SUBJ.search(p.name or "")]
    print(f"拼音 province: {len(pinyin)} 卷")
    for p in pinyin[:10]:
        print(f"  {p.province!r} → {_TEX_PROVINCE.get(p.province, '?')!r}"
              f"  ({p.name})")
    if len(pinyin) > 10:
        print(f"  ... 等共 {len(pinyin)} 卷")
    print(f"空 province: {len(empty)} 卷 → 全国")
    print(f"科别待修正(卷名带文/理尾注): {len(subjfix)} 卷")
    del n_pinyin


def main() -> None:
    apply = "--apply" in sys.argv
    with SessionLocal() as db:
        if not apply:
            _plan(db)
            print("\n以上为计划(dry-run)。执行请加 --apply")
            return
        stats = normalize_provinces(db)
        print(f"完成: province 修正 {stats['updated']} 卷, "
              f"科别修正 {stats['subject_fixed']} 卷, "
              f"合并附件卷 {stats['merged']} 卷")


if __name__ == "__main__":
    main()
