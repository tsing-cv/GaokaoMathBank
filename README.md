# GaokaoMathBank 高考数学题库

2006–2026 年全国高考数学真题的结构化题库:采集 → 清洗 → 标注 → 检索 → 成册 → 网站。

## 数据现状

- **499 卷 / 10478 题**(1952–2026 全量采集,网站按 2006–2026 展示口径)
- 年份卷数 2016 年起下降(32→6)系各省回归全国卷、自主命题缩减的历史实情,非采集缺失
- 题目带答案 **60%**、带解析 **86%**;知识点标注覆盖 82%(规则),1908 题留待 LLM 精标
- 主信源:DxAThing/Gaokao-Math-Problems-Compilation(LaTeX 重排版,CC BY-SA 4.0);
  deekur/gaokaomath(原卷 PDF 附件库,CC BY 4.0)

## 架构

```
sources.yaml ─→ collector(fetcher/ingester) ─→ SQLite(data/mathbank.db)
                    │                              │
                    │              pipeline: normalizer → tagger → dedup+FTS5
                    │                              │
                    └── data/raw/、data/assets/     ├─→ FastAPI 网站(六页面)
                                                   └─→ bookmaker(KaTeX+weasyprint 成册 PDF)
```

- **富文本分段 JSON**:`[{"t":"text|latex|img","c":"..."}]` 作为隔离层,公式保留原生 LaTeX
- **前端渲染**:网页用 KaTeX CDN;成册 PDF 用 node 进程批量服务端渲染(`bookmaker/katex_render.mjs`,
  `output:'html'` 避免 weasyprint 下 MathML 层叠印)
- **检索**:SQLite FTS5 trigram(≥3 字)+ 短词 LIKE 兜底,`<mark>` 高亮

## 快速开始

```bash
pip install -r requirements.txt
npm install katex            # 成册 PDF 的公式渲染依赖(node ≥ 18)
conda install -y -c conda-forge pango   # weasyprint 系统依赖(须与解释器同工具链)

# 1) 采集入库(首次,git clone 两个源仓库)
python tools/run_collect.py --min-year 2006 --max-year 2026

# 2) 清洗 / 标注 / 去重+全文索引(每次采集后)
python -m pipeline.normalizer
python -m pipeline.tagger          # --llm 需有效 Qwen key(见下)
python -m pipeline.dedup           # 去重 + FTS5 回填

# 3) 启动网站
uvicorn app.main:app --reload      # http://127.0.0.1:8000
```

页面:`/` 首页 · `/papers` 试卷库 · `/paper/{id}` 整卷 · `/questions` 题库检索 ·
`/topics` 知识点专题 · `/question/{id}` 题目详情 · `/books` 汇编成册。

## 成册 PDF

`/books` 页三种成册,各产出**题册 + 答案册**双 PDF(`data/books/`):

| 入口 | 说明 |
|---|---|
| 整卷汇编 | 任一试卷原卷重排 |
| 知识点专题 | 按标签聚合历年真题(上限 100 题) |
| 自选题单 | 题目 id 列表自定义组卷 |

版权页自动标注来源与协议(DxAThing CC BY-SA 4.0 / deekur CC BY 4.0)。

## 覆盖报表

```bash
python tools/stats.py --md docs/coverage.md
```

## 策略与已知边界

- **模拟题**:中国教育在线模拟频道正文为 JS 动态渲染,静态抓取不可得;GitHub 亦无
  模拟题开源仓库。接入路径:用户提供 PDF 原件走 `pdf_archive` ingester,或后续无头
  浏览器方案(`collector/ingesters/base.py` 的 HtmlIngester 基类已备)。
- **LLM 精标**:`pipeline/tagger.py --llm` 走 Qwen(兼容 DashScope);当前账号 key 返回
  403,规则标注兜底,'待标注' 题可重入精标。
- **合规**:遵守 robots.txt、并发≤3、间隔 1–3s;数据仅限个人教学研究,对外使用须
  遵循上述两仓库的 CC 协议(署名/同协议/附原始链接)。

## 测试

```bash
python -m pytest tests/ -v
```

## 🌐 在线访问 (GitHub Pages)

高考数学题库已部署到 GitHub Pages，公网可直接访问：

**🔗 访问地址：** https://tsing-cv.github.io/GaokaoMathBank/

### 主要页面

| 页面 | 地址 | 说明 |
|------|------|------|
| 首页 | https://tsing-cv.github.io/GaokaoMathBank/ | 数据概览与统计 |
| 试卷库 | https://tsing-cv.github.io/GaokaoMathBank/papers/ | 811套试卷 |
| 题库检索 | https://tsing-cv.github.io/GaokaoMathBank/questions/ | 15,608道题目 |
| 知识点专题 | https://tsing-cv.github.io/GaokaoMathBank/topics/ | 15个知识点 |

### 网站特色

- 🎨 **苹果设计语言** - 极简、专业、现代
- 📱 **响应式设计** - 完美适配桌面、平板、手机
- 🔍 **全文搜索** - 客户端搜索，快速响应
- 🌗 **暗色模式** - 自动适配系统主题
- ⚡ **CDN 加速** - 全球访问快速稳定

### 部署文档

详细的部署指南请查看：[GITHUB_PAGES_DEPLOY.md](GITHUB_PAGES_DEPLOY.md)

**快速部署：**
```bash
# 生成静态网站
python scripts/render_static.py

# 提交到 GitHub
git add docs/
git commit -m "📝 更新静态网站"
git push origin main

# GitHub Actions 自动部署到 GitHub Pages
```

### 网站统计

- 📄 **文件数：** 20,231 个
- 💾 **总大小：** 328 MB
- 📚 **试卷：** 811 套
- 📝 **题目：** 15,608 道
- 🏷️ **知识点：** 15 个

---

## 📖 相关文档

- [部署指南](GITHUB_PAGES_DEPLOY.md) - GitHub Pages 完整部署教程
- [设计指南](DESIGN_GUIDE.md) - Apple Design Language 设计规范
- [改造报告](REDESIGN_REPORT.md) - 界面设计改造总结
- [快速开始](QUICK_START.md) - 本地运行指南
