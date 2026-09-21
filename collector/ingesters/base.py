"""HTML ingester 基类:门户 adapter 的统一框架(模拟题阶段扩展用)。

子类只需实现:
- parse_list(html) -> [{url, title}]:列表页 → 试卷URL
- paper_html_to_text(html) -> str:详情页 → 纯文本(复用题号切分)
"""
from abc import ABC, abstractmethod

from selectolax.parser import HTMLParser

from collector.ingesters.pdf_archive import parse_paper_text


class HtmlIngester(ABC):
    @abstractmethod
    def parse_list(self, html: str) -> list[dict]:
        """返回 [{url, title}]"""

    @abstractmethod
    def paper_html_to_text(self, html: str) -> str:
        """详情页 DOM → 纯文本(供 parse_paper_text 复用)。"""

    def parse_paper(self, html: str, meta: dict) -> dict:
        text = self.paper_html_to_text(html)
        result = parse_paper_text(text, meta)
        result["_images"] = self.extract_images(html)
        return result

    @staticmethod
    def extract_images(html: str) -> list[str]:
        tree = HTMLParser(html)
        return [n.attributes.get("src", "") for n in tree.css("img")
                if n.attributes.get("src")]
