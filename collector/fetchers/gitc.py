"""git 合集克隆(开源 L1 来源)。"""
import subprocess
from pathlib import Path

from .base import Fetcher


class GitFetcher(Fetcher):
    async def fetch(self, entry: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # 浅克隆即可(只需要文件,不需要历史)
        subprocess.run(["git", "clone", "--depth", "1", entry, str(dest)],
                       check=True, capture_output=True)
        return dest
