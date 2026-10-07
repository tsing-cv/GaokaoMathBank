"""eol 模拟题静态解析(2026-09 实测:无需无头浏览器)。

中国教育在线"数学模拟"频道(/shiti/gkmn/sxmn/):
- 列表页静态,条目 <div class="fline"><a href="./YYYYMM/tXXX_YYY.shtml">标题</a>;
- 详情页正文为图片流(src="./W0xxxxxxxx.jpg" 相对路径,与广告/站务图
  的区别就在文件名形态),翻页是静态 _N.shtml(_PAGE_COUNT 标出总页数),
  pages.js 只做导航 → 纯 HTTP 逐页抓取即可,Playwright 不必要。

只提供纯函数;网络与入库由 tools/run_collect.py 的 eol-shiti 分支编排。
"""
import re

# 省份/卷种词表(标题里逐字匹配,长的优先防"江苏"吃到"江西省"前缀歧义)
_PROVINCES = sorted(
    ["山东", "广东", "江苏", "河北", "江西", "浙江", "安徽", "福建",
     "湖南", "湖北", "河南", "四川", "重庆", "天津", "北京", "上海",
     "陕西", "山西", "辽宁", "吉林", "黑龙江", "云南", "贵州", "广西",
     "海南", "甘肃", "青海", "宁夏", "内蒙古", "新疆", "西藏",
     "全国", "京", "津", "沪"],
    key=len, reverse=True)

# 列表条目链接(文件名 tYYYYMMDD_ID.shtml,注意含下划线)
_LIST_ITEM = re.compile(
    r'<a href="(\./20\d{4}/t[\d_]+\.shtml)">([^<]+)</a>')
# 正文图片:./W012345678901234567890.jpg 形态(eol 资源命名),排除广告绝对 URL
_BODY_IMG = re.compile(r'src="(\./W[\d]+\.(?:jpg|png|jpeg))"')
_PAGE_COUNT = re.compile(r'_PAGE_COUNT\s*=\s*"?(\d+)"?;')


def parse_list_page(html: str) -> list[tuple[str, str]]:
    """列表页 → [(相对链接, 标题)]。过滤真题/导航条目、去重保序。"""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for url, title in _LIST_ITEM.findall(html):
        title = title.strip()
        if url in seen or not title:
            continue
        if "真题" in title:  # 频道混推的真题条目不属于本源
            continue
        if "数学" not in title:
            # 本频道是数学模拟题列表,不含"数学"的是"详细"等
            # 导航链接文案(2026-09-22 曾入库一卷名为"详细"的垃圾卷)
            continue
        seen.add(url)
        out.append((url, title))
    return out


def parse_paper_page(html: str) -> dict:
    """详情单页 → {pages: 总页数, images: [正文图片相对路径]}。"""
    m = _PAGE_COUNT.search(html)
    imgs = _BODY_IMG.findall(html)
    # 去重保序(同一图可能被懒加载标签写两次)
    seen: set[str] = set()
    uniq = [i for i in imgs if not (i in seen or seen.add(i))]
    return {"pages": int(m.group(1)) if m else 1, "images": uniq}


def meta_from_title(title: str) -> dict:
    """标题 → meta:年份/省份/科别/exam_type=模拟。

    "2021年山东省高考模拟题:数学" → 山东/文理同卷;
    "2018高考模拟试题及答案(一):数学(理)" → 通用/理科(无地域词)。
    """
    year = 0
    m = re.match(r"\s*(\d{4})", title)
    if m:
        year = int(m.group(1))
    province = "通用"
    for p in _PROVINCES:
        if p in title:
            province = p
            break
    subject = "文理同卷"
    if re.search(r"[（(]文[）)]|文科", title):
        subject = "文科"
    elif re.search(r"[（(]理[）)]|理科", title):
        subject = "理科"
    return {"year": year, "province": province, "exam_type": "模拟",
            "subject": subject, "name": title}


def paginated_urls(detail_url: str, pages: int) -> list[str]:
    """详情首页 URL + _1.._N 翻页 URL。"""
    stem = detail_url[: detail_url.rfind(".")]  # 去 .shtml
    return [detail_url] + [f"{stem}_{i}.shtml" for i in range(1, pages)]
