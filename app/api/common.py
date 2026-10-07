"""API 路由共用工具。"""
from typing import Annotated, Optional

from pydantic import BeforeValidator


def _blank_to_none(v):
    """表单空值(select 未选)提交的 "" 归 None。

    HTML 表单的 select 即使未选中也会提交空串(year=),FastAPI 对
    int 参数的空串解析直接 422(2026-09-22 /questions 检索实测)。
    """
    return None if v in (None, "") else v


# 可选 int 查询参数:声明处写作 year: OptIntQuery = None
OptIntQuery = Annotated[Optional[int], BeforeValidator(_blank_to_none)]
