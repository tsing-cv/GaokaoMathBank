"""全库 latex 段导出为 katex_audit.mjs 的 stdin JSON。

用法:python tools/latex_audit.py | node bookmaker/katex_audit.mjs
"""
import json
import sqlite3
import sys

sys.path.insert(0, ".")


def main() -> None:
    db = sqlite3.connect("data/mathbank.db")
    items = []
    for (stem, opts, ans, ana) in db.execute(
            "SELECT stem, options, answer, analysis FROM questions"):
        segs = []
        for v in (stem, ans, ana):
            segs += json.loads(v) if isinstance(v, str) else (v or [])
        for o in (json.loads(opts) if isinstance(opts, str) else (opts or [])):
            segs += o.get("segs") or []
        items.extend({"tex": s["c"]} for s in segs if s.get("t") == "latex" and s.get("c"))
    print(json.dumps({"items": items}, ensure_ascii=False))


if __name__ == "__main__":
    main()
