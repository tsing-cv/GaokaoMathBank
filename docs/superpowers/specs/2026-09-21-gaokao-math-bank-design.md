# GaokaoMathBank 高考数学题库系统 — 设计文档

日期:2026-09-21
状态:已确认(用户于设计评审中批准)

## 1. 项目目标

抓取 2006-2026 年全国各地高考数学真题及模拟考题(官方模考、大型联考、机构名卷),结构化为统一题库,支持:

- 网站检索浏览(个人/教学用途,校内访问,无账号系统)
- 按年份-省份 / 知识点专题 / 自选题单汇编成册(PDF 导出)

### 已确认的边界决策

| 决策点 | 结论 |
|---|---|
| 用途 | 个人/教学使用,标注来源即可,不做公开运营 |
| 采集范围 | 真题全量 + 官方模考 + 大型联考 + 机构名卷(衡水卷、金太阳等),分优先级渐进覆盖 |
| 内容深度 | 题目 + 答案 + 解析(来源有则抓,无则标记待补) |
| 技术形态 | FastAPI 动态网站(SQLite),类 ShuiwenJiankong 模式 |
| 采集策略 | 开源合集 + 官方 PDF 优先,门户爬虫补缺 |
| 时间跨度 | 2006-2026(21 年) |

## 2. 总体架构

```
GaokaoMathBank/
├── app/                  # FastAPI 网站(展示层)
│   ├── main.py           # 一体化托管:Jinja2 SSR + 静态资源 + API
│   ├── api/              # 路由:papers / questions / topics / books / assets
│   ├── models.py         # SQLAlchemy 模型
│   └── templates/        # 简洁教学风模板 + KaTeX 公式渲染
├── collector/            # 采集子系统(数据层入口)
│   ├── sources.yaml      # 来源注册表(分级 L1/L2/L3)
│   ├── fetchers/         # git 下载器 / PDF 下载器 / HTML 爬虫(每站一 adapter)
│   └── ingesters/        # PDF→题目 / HTML→题目 解析器
├── pipeline/             # 处理管线
│   ├── normalizer.py     # 清洗:去水印/广告/导航噪音;公式统一转 LaTeX
│   ├── tagger.py         # 知识点标注:关键词规则初标 + LLM 精标
│   └── dedup.py          # source_hash 去重(多站转载同一卷)
├── bookmaker/            # 汇编成册:weasyprint(HTML 模板→PDF)
├── data/                 # SQLite 库 + 原始文件归档(pdf/图片)
├── tools/                # 运维脚本:统计报表、重跑、校验
├── tests/                # pytest
├── run.sh                # 一键启动
└── requirements.txt
```

数据流向(单向):

```
sources.yaml → fetcher(下载原始文件)→ ingester(结构化解析)
→ normalizer(清洗+公式标准化)→ tagger(知识点标注)→ dedup → SQLite
→ FastAPI 网站 / bookmaker PDF 成册
```

## 3. 数据模型(SQLite)

### papers(试卷)

| 字段 | 说明 |
|---|---|
| id | 主键 |
| year | 年份 2006-2026 |
| province | 省份/卷种(全国甲卷、新高考I卷、北京、上海、江苏…) |
| exam_type | 真题 / 一模 / 二模 / 三模 / 联考 / 机构卷 |
| subject | 理科 / 文科 / 新高考 / 通用 |
| name | 卷面名称(如"2024年全国新高考I卷数学") |
| source_name / source_url | 来源标注(合规要求) |
| pdf_path | 原卷 PDF 本地路径(兜底附件,永远保留) |
| status | pending / parsed / partial / failed |
| question_count | 题目数 |

### questions(题目)

| 字段 | 说明 |
|---|---|
| id | 主键 |
| paper_id | 外键 → papers |
| seq | 题号 |
| qtype | 选择 / 填空 / 解答 |
| stem | 题干,富文本分段 JSON(见下) |
| options | 选项 JSON(A/B/C/D 各为分段 JSON) |
| answer | 答案(文本/分段 JSON) |
| analysis | 解析(分段 JSON,可空) |
| knowledge_tags | 知识点标签 JSON 数组 |
| difficulty | 预留(暂不标注) |
| source_hash | 去重指纹(stem 规范化 hash) |

### assets(资源)

题目配图、公式截图:url、本地路径、所属 question_id、kind(figure/formula_img)。

### 题干富文本统一格式(核心设计)

所有文本字段(stem/options/answer/analysis)统一为分段数组,每段三选一:

```json
[
  {"t": "text",  "c": "已知函数"},
  {"t": "latex", "c": "f(x)=\\ln x - ax"},
  {"t": "img",   "c": "/assets/q123_f1.png"}
]
```

- 前端按段渲染:text 直接输出、latex 走 KaTeX、img 输出图片
- 这是应对来源公式格式混乱(LaTeX 定界符/图片公式/Unicode 伪公式)的统一出口
- 转不成 LaTeX 的公式一律保留原图,不强行转换

## 4. 采集子系统

### 来源分级

| 级别 | 来源 | 方式 | 用途 |
|---|---|---|---|
| L1 | GitHub 开源真题合集、公开网盘整理集 | git clone / 批量下载 | 真题覆盖主力 |
| L2 | 省考试院官网、教育部阳光高考、教育门户官方 PDF | PDF 下载 | 权威性兜底 |
| L3 | 中国教育在线、无忧考网、高考网等公开试题页 | HTML 爬虫(每站一 adapter) | 结构化补缺 + 模拟题 |

### sources.yaml 来源注册表

每个来源声明:type(git/pdf_archive/html_site)、入口 URL、覆盖范围(year/province/exam_type)、抓取策略(频控/深度)、解析器名。新增来源只改配置+可选新 adapter。

### 合规约束

- 遵守目标站 robots.txt
- 并发 ≤ 3,请求间隔随机 1-3s
- 超时指数退避重试,最多 3 次
- 所有入库数据带 source_name/source_url 标注
- 仅用于个人教学研究

## 5. 处理管线

1. **normalizer**:去水印/页眉页脚/广告/导航噪音;识别题号切分;公式检测与 LaTeX 标准化(统一 `$...$` 定界符)
2. **tagger**:约 15 个一级知识点(集合与逻辑/函数/导数/三角/数列/立体几何/解析几何/概率统计/向量/复数/不等式/排列组合/极坐标与参数方程/数学文化/综合);关键词规则初标,不确定的交 LLM 批量精标(失败重试,兜底标"待标注")
3. **dedup**:同一试卷多站转载 → 按(年份+省份+类型+名称相似度)卷级去重;题目级按 source_hash

## 6. 网站(FastAPI + Jinja2 SSR + KaTeX + 原生 JS)

| 路由 | 功能 |
|---|---|
| `/` | 仪表盘:总卷/题数、年份×省份覆盖热力表、最近入库 |
| `/papers` | 筛选(年份/省份/类型/科目)+ 分页列表 |
| `/paper/{id}` | 整卷视图:按题号还原试卷结构,答案/解析折叠可展开(自测场景),原卷 PDF 下载 |
| `/questions` | 跨卷检索:FTS5 全文 + 知识点 + 题型 + 年份区间 |
| `/question/{id}` | 题目详情 + 同知识点相关题 |
| `/topics` | 知识点专题聚合页 |
| `/books` | 成册中心:年份-省份成册 / 知识点专题成册 / 自选题单(存 localStorage)→ weasyprint 生成 PDF |

## 7. 汇编成册(bookmaker)

- weasyprint:HTML 模板(封面/目录/页眉页脚/分页)→ PDF
- 三种成册维度:按年份-省份(整卷合集)、按知识点专题(跨年选题)、自选题单
- 生成任务同步执行(个人使用,量小),产物缓存于 data/books/

## 8. 错误处理

| 环节 | 策略 |
|---|---|
| 抓取 | 超时/5xx 指数退避重试≤3;连续失败标记来源为 degraded |
| 解析 | 单卷失败进 failed 状态保留原始文件,不阻塞批次;可重跑 |
| 公式 | 转换失败保留原图,不丢数据 |
| LLM 标注 | 超时重试;最终兜底"待标注"标签 |
| 网站 | 404/500 统一错误页;数据库不存在时引导先跑采集 |

## 9. 测试策略

- pytest 单测:normalizer(脏格式样本)、ingesters(PDF/HTML 样本文件)、dedup、题干分段 JSON 序列化
- API 测试:路由返回、筛选组合、FTS 检索
- 端到端:用一个小型样本源跑通 fetch→ingest→normalize→tag→查询全链路

## 10. 实施阶段

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| P1 基础设施 | 骨架、模型、网站空跑、测试框架 | `run.sh` 启动空网站,pytest 绿 |
| P2 真题采集 | L1/L2 接入,真题批量入库 | 真题覆盖统计报表可见 |
| P3 数据处理 | 清洗、公式渲染、知识点标注 | 网站可正常渲染公式、检索 |
| P4 网站成册 | 完整功能 + PDF 成册 | 三种成册可下载 |
| P5 模拟题+审查 | 模考/联考/机构卷分批采集,整体审查优化 | 覆盖报表 + 全链路审查清单通过 |

## 11. 风险与对策

1. **公式格式混乱(最大风险)** → 分段 JSON 统一出口;失败保留原图;原卷 PDF 永远可下载
2. **模拟题海量** → 优先级批次渐进,不追求一次抓完
3. **多站转载重复** → 卷级+题级双重去重
4. **LLM 标注成本** → 规则初标过滤,LLM 只处理不确定子集
5. **来源失效** → 来源注册表化,单来源故障不影响整体
