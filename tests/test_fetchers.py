import asyncio
from collector.fetchers.base import Fetcher, retry


def test_retry_eventually_succeeds():
    calls = {"n": 0}

    @retry(times=3, base_delay=0.01)
    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("boom")
        return "ok"

    assert asyncio.run(flaky()) == "ok" and calls["n"] == 3


def test_retry_gives_up():
    @retry(times=3, base_delay=0.01)
    async def always_fail():
        raise ConnectionError("boom")

    try:
        asyncio.run(always_fail())
        assert False, "应当抛出"
    except ConnectionError:
        pass


def test_fetchers_are_subclasses():
    from collector.fetchers.html import HtmlFetcher
    from collector.fetchers.gitc import GitFetcher
    from collector.fetchers.pdf import PdfFetcher
    assert issubclass(HtmlFetcher, Fetcher)
    assert issubclass(GitFetcher, Fetcher)
    assert issubclass(PdfFetcher, Fetcher)
