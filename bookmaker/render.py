"""分段 JSON → 成册 HTML:KaTeX 服务端批量渲染(node 一次进程)+ 失败降级。"""
import json
import subprocess
from pathlib import Path

from app import ROOT
from app.segments import fix_latex as _fix_tex  # noqa: F401(统一清洗入口)

MJS = Path(__file__).parent / "katex_render.mjs"
KATEX_DIST = ROOT / "node_modules" / "katex" / "dist"

_latex_cache: dict[str, str] = {}


def render_latex_batch(items: list[tuple[str, bool]]) -> dict[str, str]:
    """[(latex, display)] → {latex\x00display: html}。失败项降级为空(调用方回退)。

    单次 node 进程批量渲染,显著快于逐段调用。
    """
    uniq: dict[str, dict] = {}
    for tex, display in items:
        uniq.setdefault(f"{tex}\x00{display}", {"tex": tex, "display": display})
    if not uniq:
        return {}
    payload = json.dumps({"items": list(uniq.values())})
    try:
        r = subprocess.run(["node", str(MJS)], input=payload.encode(),
                           capture_output=True, timeout=120, cwd=str(ROOT))
        got = json.loads(r.stdout)
    except Exception:
        return {}
    out: dict[str, str] = {}
    for key, i in zip(uniq.keys(), range(len(uniq))):
        html = got.get(str(i))
        if html:
            out[key] = html
    return out


def segs_to_html(segs: list[dict], rendered: dict[str, str] | None = None) -> str:
    """分段 → HTML 字符串。rendered 为预渲染表;latex 未命中时降级 <code>。

    text 段做 HTML 转义;img 段输出 <img>(src 为 /assets/... web 路径,
    成册场景改写为 data/assets 绝对路径由 book.py 处理)。
    """
    parts: list[str] = []
    for s in segs or []:
        if s["t"] == "text":
            t = (s["c"] or "").replace("&", "&amp;").replace("<", "&lt;") \
                              .replace(">", "&gt;")
            parts.append(f'<span class="tx">{t}</span>')
        elif s["t"] == "latex":
            tex = _fix_tex(s["c"])
            html = (rendered or {}).get(f"{tex}\x00False")
            html_d = (rendered or {}).get(f"{tex}\x00True")
            if s.get("display") and html_d:
                parts.append(f'<div class="dp">{html_d}</div>')
            elif html:
                parts.append(html)
            elif html_d:  # 只有 display 版本也接受
                parts.append(f'<div class="dp">{html_d}</div>')
            else:
                safe = tex.replace("&", "&amp;").replace("<", "&lt;")
                parts.append(f"<code>${safe}$</code>")
        else:  # img
            parts.append(f'<img class="qimg" src="{s["c"]}">')
    return "".join(parts)


def collect_latex(questions: list[dict]) -> list[tuple[str, bool]]:
    """扫描全部题目的 latex 段,返回 [(tex, display=False)](统一行内渲染)。"""
    out: set[str] = set()
    for q in questions:
        for field in ("stem", "answer", "analysis"):
            for s in q.get(field) or []:
                if s["t"] == "latex":
                    out.add(_fix_tex(s["c"]))
        for o in q.get("options") or []:
            for s in o.get("segs") or []:
                if s["t"] == "latex":
                    out.add(_fix_tex(s["c"]))
    return [(t, False) for t in out]
