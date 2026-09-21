"""HTML 页面抓取器(带磁盘缓存,重复抓取不重新请求)。"""
import hashlib
from pathlib import Path

import httpx

from app import RAW_DIR
from .base import UA, Fetcher, retry


class HtmlFetcher(Fetcher):
    cache_dir = RAW_DIR / "html"

    @retry(times=3)
    async def _get(self, url: str) -> str:
        async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=30,
                                     follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            r.encoding = r.charset_encoding or "utf-8"
            return r.text

    async def fetch_page(self, url: str) -> str:
        """抓单页;命中缓存直接返回磁盘内容。"""
        h = hashlib.md5(url.encode()).hexdigest()
        cache = self.cache_dir / f"{h}.html"
        if cache.exists():
            return cache.read_text(encoding="utf-8")
        text = await self._bounded(self._get(url))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, encoding="utf-8")
        return text

    async def fetch(self, entry: str, dest: Path) -> Path:  # 统一接口:存到指定文件
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(await self.fetch_page(entry), encoding="utf-8")
        return dest
