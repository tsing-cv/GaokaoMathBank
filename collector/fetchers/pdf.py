"""PDF 文件下载器。"""
from pathlib import Path

import httpx

from .base import UA, Fetcher, retry


class PdfFetcher(Fetcher):
    @retry(times=3)
    async def _dl(self, url: str, dest: Path) -> Path:
        async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=60,
                                     follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return dest

    async def fetch(self, entry: str, dest: Path) -> Path:
        return await self._bounded(self._dl(entry, dest))
