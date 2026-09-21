"""Fetcher 基类:合规频控 + 指数退避重试。"""
import asyncio
import functools
import random
from abc import ABC, abstractmethod
from pathlib import Path

UA = "GaokaoMathBank/0.1 (personal-study)"
MAX_CONCURRENCY = 3          # 设计约束:并发≤3
_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)


def retry(times: int = 3, base_delay: float = 1.0):
    """指数退避重试装饰器:失败翻倍延迟,最多 times 次。"""
    def deco(fn):
        @functools.wraps(fn)
        async def wrapper(*a, **kw):
            delay = base_delay
            for i in range(times):
                try:
                    return await fn(*a, **kw)
                except Exception:
                    if i == times - 1:
                        raise
                    await asyncio.sleep(delay + random.random())
                    delay *= 2
        return wrapper
    return deco


async def politeness():
    """随机 1-3s 礼貌间隔(设计约束)。"""
    await asyncio.sleep(1 + random.random() * 2)


class Fetcher(ABC):
    @abstractmethod
    async def fetch(self, entry: str, dest: Path) -> Path: ...

    async def _bounded(self, coro):
        """并发限制 + 礼貌间隔包装。"""
        async with _semaphore:
            await politeness()
            return await coro
