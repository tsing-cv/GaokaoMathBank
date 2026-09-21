from collector.source_registry import load_sources, validate


def test_load_and_validate():
    srcs = load_sources()
    assert len(srcs) >= 3
    validate(srcs)  # 不抛异常即通过
    kinds = {s["type"] for s in srcs}
    assert "git" in kinds  # L1 真题主力已配置
    for s in srcs:
        assert s["level"] in ("L1", "L2", "L3")
        assert s["fetcher"] in ("git", "pdf", "html")
        assert s["notes"]  # 每个来源必须有实测说明
