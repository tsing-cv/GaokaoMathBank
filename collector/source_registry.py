"""来源注册表加载与校验。"""
import pathlib

import yaml

SRC_FILE = pathlib.Path(__file__).parent / "sources.yaml"
FETCHERS = {"git", "pdf", "html"}
LEVELS = {"L1", "L2", "L3"}


def load_sources() -> list[dict]:
    with open(SRC_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["sources"]


def validate(srcs: list[dict]) -> None:
    names = set()
    for s in srcs:
        for k in ("name", "level", "type", "entry", "fetcher", "ingester"):
            if not s.get(k):
                raise ValueError(f"来源缺少字段 {k}: {s}")
        if s["fetcher"] not in FETCHERS or s["level"] not in LEVELS:
            raise ValueError(f"来源字段非法: {s['name']}")
        if s["name"] in names:
            raise ValueError(f"来源重名: {s['name']}")
        names.add(s["name"])
