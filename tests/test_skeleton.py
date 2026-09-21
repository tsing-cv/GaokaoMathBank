"""骨架自检:包可导入。"""


def test_packages_importable():
    import app  # noqa: F401
    import collector  # noqa: F401
    import pipeline  # noqa: F401
    import bookmaker  # noqa: F401
