"""PDF 生成独立 worker:weasyprint+pango 若在进程清理阶段 SIGABRT
(PDF 已完整写出),子进程隔离可避免伤及主服务。

pango 依赖经 conda-forge 安装于 anaconda lib(与解释器同工具链,
避免混链 homebrew 库的 ABI 冲突段错误)。

用法:python -m bookmaker.pdf_worker <in.html> <out.pdf>
"""
import sys
from pathlib import Path

from weasyprint import HTML

from bookmaker.render import KATEX_DIST


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    html = HTML(string=src.read_text(encoding="utf-8"),
                base_url=str(KATEX_DIST))
    dst.parent.mkdir(parents=True, exist_ok=True)
    html.write_pdf(dst)
    print(f"written: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
