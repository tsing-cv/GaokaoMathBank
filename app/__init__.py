"""GaokaoMathBank 应用包。"""
import pathlib

# 项目根与数据路径(全模块共用)
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "mathbank.db"
ASSETS_DIR = DATA_DIR / "assets"
RAW_DIR = DATA_DIR / "raw"
BOOKS_DIR = DATA_DIR / "books"
for _d in (DATA_DIR, ASSETS_DIR, RAW_DIR, BOOKS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
