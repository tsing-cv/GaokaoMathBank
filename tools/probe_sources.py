"""来源探活:检查 entry 可达性 + robots.txt 是否允许抓取。

用法:python tools/probe_sources.py [来源名]
"""
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collector.source_registry import load_sources  # noqa: E402

UA = "GaokaoMathBank/0.1 (personal-study)"


async def probe(client: httpx.AsyncClient, src: dict) -> dict:
    """探测单个来源:entry 可达 + robots 粗查。"""
    try:
        r = await client.get(src["entry"], follow_redirects=True, timeout=20)
        ok, code = r.status_code < 400, r.status_code
    except Exception as e:
        ok, code = False, str(e)[:80]
    robots_ok = True
    robots_note = ""
    try:
        o = urlparse(src["entry"])
        rb = await client.get(f"{o.scheme}://{o.netloc}/robots.txt", timeout=10)
        if rb.status_code == 200:
            # 粗查:是否存在全站 Disallow(精确解析在 fetcher 层按路径做)
            lines = [ln.strip() for ln in rb.text.splitlines() if ln.strip()]
            ua_match = False
            disallow_all = False
            for ln in lines:
                low = ln.lower()
                if low.startswith("user-agent:"):
                    ua_match = "*" in low or "gaokaomath" in low
                elif ua_match and low.startswith("disallow: /") and low.strip() == "disallow: /":
                    disallow_all = True
            robots_ok = not disallow_all
            robots_note = f"robots {'允许' if robots_ok else '全站禁止'}"
        else:
            robots_note = f"robots http {rb.status_code}"
    except Exception as e:
        robots_note = f"robots 不可达({str(e)[:40]})"
    return {"name": src["name"], "ok": ok, "code": code,
            "robots_ok": robots_ok, "note": robots_note}


async def main(only: str | None):
    async with httpx.AsyncClient(headers={"User-Agent": UA},
                                 follow_redirects=True) as c:
        for src in load_sources():
            if only and src["name"] != only:
                continue
            r = await probe(c, src)
            flag = "✅" if r["ok"] and r["robots_ok"] else "❌"
            print(f"{flag} {r['name']:<22} 可达={r['ok']} code={r['code']} {r['note']}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
