"""FastAPI 一体化入口:SSR 页面 + 静态资源。"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import ROOT, ASSETS_DIR
from .api import dashboard, papers

app = FastAPI(title="GaokaoMathBank 高考数学题库")
app.include_router(dashboard.router)
app.include_router(papers.router)
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
# 题目图片资源:直接托管 data/assets
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
