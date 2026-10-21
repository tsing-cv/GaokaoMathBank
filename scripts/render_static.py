# -*- coding: utf-8 -*-
"""
静态网站生成器 - 将 FastAPI 动态网站预渲染为静态 HTML
用于 GitHub Pages 部署
"""
import json
import sqlite3
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import shutil
import sys

# 路径配置
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "mathbank.db"
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"
OUTPUT_DIR = BASE_DIR / "docs"  # GitHub Pages 使用 docs 目录

# GitHub Pages 基础路径
BASE_PATH = "/GaokaoMathBank"

# Jinja2 环境
env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=True
)

# 添加全局变量
env.globals["BASE_PATH"] = BASE_PATH

# 添加自定义过滤器
def format_number(value):
    """格式化数字（千分位）"""
    if value is None:
        return "0"
    return f"{value:,}"

env.filters["format_number"] = format_number



def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def export_complete_data():
    """导出完整数据为 JSON"""
    print("\n📦 导出数据...")
    conn = get_db()

    # 1. 导出试卷列表
    print("  → 导出试卷列表...")
    papers = conn.execute("""
        SELECT id, year, province, exam_type, subject, name, question_count
        FROM papers WHERE question_count > 0
        ORDER BY year DESC, province
    """).fetchall()

    papers_data = [dict(p) for p in papers]

    # 2. 导出题目（完整版，含解析）
    print("  → 导出题目数据...")
    questions = conn.execute("""
        SELECT q.id, q.paper_id, q.seq, q.qtype, q.stem, q.options,
               q.answer, q.analysis, q.knowledge_tags, q.difficulty,
               p.year, p.province, p.name as paper_name
        FROM questions q
        JOIN papers p ON q.paper_id = p.id
        ORDER BY p.year DESC, q.seq
    """).fetchall()

    questions_data = []
    for q in questions:
        q_dict = dict(q)
        q_dict["stem"] = json.loads(q_dict["stem"]) if q_dict["stem"] else []
        q_dict["options"] = json.loads(q_dict["options"]) if q_dict["options"] else []
        q_dict["answer"] = json.loads(q_dict["answer"]) if q_dict["answer"] else []
        q_dict["analysis"] = json.loads(q_dict["analysis"]) if q_dict["analysis"] else []
        q_dict["knowledge_tags"] = json.loads(q_dict["knowledge_tags"]) if q_dict["knowledge_tags"] else []
        questions_data.append(q_dict)

    # 3. 导出知识点统计
    print("  → 导出知识点统计...")
    tag_counts = {}
    for q in questions_data:
        for tag in q["knowledge_tags"]:
            if tag and tag != "待标注":
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    tags_data = [{"name": k, "count": v} for k, v in sorted(tag_counts.items(), key=lambda x: -x[1])]

    # 4. 导出筛选选项
    years = sorted(set(p["year"] for p in papers_data), reverse=True)
    provinces = sorted(set(p["province"] for p in papers_data if p["province"]))
    exam_types = sorted(set(p["exam_type"] for p in papers_data if p["exam_type"]))
    subjects = sorted(set(p["subject"] for p in papers_data if p["subject"]))

    filters_data = {
        "years": years,
        "provinces": provinces,
        "exam_types": exam_types,
        "subjects": subjects
    }

    # 5. 统计信息
    stats_data = {
        "total_papers": len(papers_data),
        "total_questions": len(questions_data),
        "years": years,
        "provinces": provinces,
        "exam_types": exam_types,
        "qtypes": sorted(set(q["qtype"] for q in questions_data if q["qtype"])),
        "generated_at": datetime.now().isoformat()
    }

    conn.close()

    return {
        "papers": papers_data,
        "questions": questions_data,
        "tags": tags_data,
        "filters": filters_data,
        "stats": stats_data
    }


def render_index(data, output_dir):
    """渲染首页"""
    print("  → 渲染首页...")
    template = env.get_template("index.html")

    # 按年份分组试卷
    years_data = []
    years = sorted(set(p["year"] for p in data["papers"]), reverse=True)

    for year in years[:20]:  # 只显示最近20年
        year_papers = [p for p in data["papers"] if p["year"] == year]
        year_questions = [q for q in data["questions"] if q["year"] == year]

        years_data.append({
            "year": year,
            "papers": year_papers,
            "n_q": len(year_questions)
        })

    html = template.render(
        paper_total=data["stats"]["total_papers"],
        q_total=data["stats"]["total_questions"],
        years=years_data,
        chips_max=6,
        BASE_PATH=BASE_PATH,
        request={"url": {"path": "/"}}
    )

    (output_dir / "index.html").write_text(html, encoding="utf-8")


def render_papers(data, output_dir):
    """渲染试卷列表页"""
    print("  → 渲染试卷库...")
    template = env.get_template("papers.html")

    # 按年份分组
    papers_by_year = {}
    for p in data["papers"]:
        year = p["year"]
        if year not in papers_by_year:
            papers_by_year[year] = []
        papers_by_year[year].append(p)

    # 当前筛选条件（静态网站不需要）
    cur = {
        "year": "",
        "province": "",
        "subject": "",
        "exam_type": ""
    }

    html = template.render(
        total=len(data["papers"]),
        papers=data["papers"],
        papers_by_year=papers_by_year,
        years=data["filters"]["years"],
        provinces=data["filters"]["provinces"],
        subjects=data["filters"]["subjects"],
        cur=cur,
        pages=1,
        request={"url": {"path": "/papers"}}
    )

    papers_dir = output_dir / "papers"
    papers_dir.mkdir(exist_ok=True)
    (papers_dir / "index.html").write_text(html, encoding="utf-8")


def render_paper_detail(data, output_dir):
    """渲染每个试卷详情页"""
    print("  → 渲染试卷详情页...")
    template = env.get_template("paper_detail.html")

    paper_dir = output_dir / "paper"
    paper_dir.mkdir(exist_ok=True)

    count = 0
    for paper in data["papers"]:
        paper_questions = [q for q in data["questions"] if q["paper_id"] == paper["id"]]

        html = template.render(
            paper=paper,
            questions=paper_questions,
            BASE_PATH=BASE_PATH,
        request={"url": {"path": f"/paper/{paper['id']}"}}
        )

        (paper_dir / f"{paper['id']}.html").write_text(html, encoding="utf-8")
        count += 1

        if count % 100 == 0:
            print(f"    已渲染 {count} 个试卷...")

    print(f"    ✓ 完成 {count} 个试卷详情页")


def segments_to_html(segments):
    """将分段 JSON 转换为 HTML"""
    if not segments:
        return ""

    html_parts = []
    for seg in segments:
        if seg.get("t") == "text":
            html_parts.append(seg.get("c", ""))
        elif seg.get("t") == "latex":
            html_parts.append(f"${seg.get('c', '')}$")
        elif seg.get("t") == "img":
            html_parts.append(f'<img src="{seg.get("c", "")}" class="qimg">')

    return "".join(html_parts)


def render_questions(data, output_dir):
    """渲染题目检索页"""
    print("  → 渲染题库检索...")
    template = env.get_template("questions.html")

    # 只显示前100题作为示例
    sample_questions = data["questions"][:100]

    # 为每个题目生成 HTML 格式的题目内容
    items = []
    for q in sample_questions:
        # 生成题目 HTML（截取前200字符）
        stem_html = segments_to_html(q["stem"])
        if len(stem_html) > 200:
            stem_html = stem_html[:200] + "..."

        items.append({
            "id": q["id"],
            "html": stem_html,
            "year": q["year"],
            "paper_id": q["paper_id"],
            "paper_name": q["paper_name"],
            "qtype": q["qtype"],
            "has_answer": bool(q.get("answer")),
            "has_analysis": bool(q.get("analysis")),
            "tags": q.get("knowledge_tags", [])
        })

    # 当前搜索条件（静态网站不需要）
    cur = {
        "q": "",
        "tag": "",
        "qtype": "",
        "year": ""
    }

    html = template.render(
        total=len(data["questions"]),
        items=items,
        cur=cur,
        years=data["filters"]["years"],
        page=1,
        pages=1,
        request={"url": {"path": "/questions"}}
    )

    questions_dir = output_dir / "questions"
    questions_dir.mkdir(exist_ok=True)
    (questions_dir / "index.html").write_text(html, encoding="utf-8")


def render_question_detail(data, output_dir):
    """渲染每个题目详情页"""
    print("  → 渲染题目详情页...")
    template = env.get_template("question_detail.html")

    # 创建 paper 字典以便快速查找
    papers_dict = {p["id"]: p for p in data["papers"]}

    question_dir = output_dir / "question"
    question_dir.mkdir(exist_ok=True)

    count = 0
    for question in data["questions"]:
        # 获取试卷信息
        paper = papers_dict.get(question["paper_id"])

        # 找到相关题目（相同知识点）
        related = []
        if question["knowledge_tags"]:
            for q in data["questions"]:
                if q["id"] != question["id"] and any(
                    tag in q["knowledge_tags"] for tag in question["knowledge_tags"]
                ):
                    # 添加 segs 和 name 字段
                    q_with_segs = q.copy()
                    q_with_segs["segs"] = q["stem"]
                    q_with_segs["name"] = q.get("paper_name", "")
                    related.append(q_with_segs)
                    if len(related) >= 5:
                        break

        html = template.render(
            q=question,
            paper=paper,
            related=related,
            BASE_PATH=BASE_PATH,
        request={"url": {"path": f"/question/{question['id']}"}}
        )

        (question_dir / f"{question['id']}.html").write_text(html, encoding="utf-8")
        count += 1

        if count % 500 == 0:
            print(f"    已渲染 {count} 个题目...")

    print(f"    ✓ 完成 {count} 个题目详情页")


def render_topics(data, output_dir):
    """渲染知识点专题页"""
    print("  → 渲染知识点专题...")
    template = env.get_template("topics.html")

    # 知识点概览模式
    counts = [{"tag": t["name"], "n": t["count"]} for t in data["tags"]]

    html = template.render(
        overview=True,
        counts=counts,
        BASE_PATH=BASE_PATH,
        request={"url": {"path": "/topics"}}
    )

    topics_dir = output_dir / "topics"
    topics_dir.mkdir(exist_ok=True)
    (topics_dir / "index.html").write_text(html, encoding="utf-8")


def copy_static_files(output_dir):
    """复制静态资源"""
    print("  → 复制静态资源...")

    # 创建 static 目录
    static_output = output_dir / "static"
    static_output.mkdir(exist_ok=True)

    # 复制 CSS 文件
    for css_file in STATIC_DIR.glob("*.css"):
        shutil.copy2(css_file, static_output / css_file.name)

    # 复制 JS 文件（如果有）
    for js_file in STATIC_DIR.glob("*.js"):
        shutil.copy2(js_file, static_output / js_file.name)

    # 复制 KaTeX 子目录（如果存在）
    katex_dir = STATIC_DIR / "katex"
    if katex_dir.exists():
        katex_output = static_output / "katex"
        if not katex_output.exists():
            shutil.copytree(katex_dir, katex_output)

    # 复制图片资源（如果存在）
    assets_dir = BASE_DIR / "data" / "assets"
    if assets_dir.exists():
        assets_output = output_dir / "assets"
        if not assets_output.exists():
            shutil.copytree(assets_dir, assets_output)


def export_json_data(data, output_dir):
    """导出 JSON 数据供客户端使用"""
    print("  → 导出 JSON 数据...")

    data_dir = output_dir / "data"
    data_dir.mkdir(exist_ok=True)

    # 导出各个数据集
    with open(data_dir / "papers.json", "w", encoding="utf-8") as f:
        json.dump(data["papers"], f, ensure_ascii=False, indent=2)

    with open(data_dir / "questions.json", "w", encoding="utf-8") as f:
        # 精简版题目数据（不含长解析）
        questions_lite = []
        for q in data["questions"]:
            q_lite = {k: v for k, v in q.items() if k != "analysis"}
            questions_lite.append(q_lite)
        json.dump(questions_lite, f, ensure_ascii=False, indent=2)

    with open(data_dir / "tags.json", "w", encoding="utf-8") as f:
        json.dump(data["tags"], f, ensure_ascii=False, indent=2)

    with open(data_dir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(data["stats"], f, ensure_ascii=False, indent=2)

    with open(data_dir / "filters.json", "w", encoding="utf-8") as f:
        json.dump(data["filters"], f, ensure_ascii=False, indent=2)


def generate_sitemap(output_dir):
    """生成站点地图"""
    print("  → 生成站点地图...")

    base_url = "https://tsing-cv.github.io/GaokaoMathBank"

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # 添加主要页面
    pages = [
        ("/", "1.0", "daily"),
        ("/papers/", "0.9", "weekly"),
        ("/questions/", "0.9", "weekly"),
        ("/topics/", "0.8", "weekly"),
    ]

    for path, priority, changefreq in pages:
        sitemap.append(f"""
  <url>
    <loc>{base_url}{path}</loc>
    <priority>{priority}</priority>
    <changefreq>{changefreq}</changefreq>
  </url>
""")

    sitemap.append("</urlset>")

    (output_dir / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")


def generate_robots_txt(output_dir):
    """生成 robots.txt"""
    print("  → 生成 robots.txt...")

    content = """User-agent: *
Allow: /

Sitemap: https://tsing-cv.github.io/GaokaoMathBank/sitemap.xml
"""

    (output_dir / "robots.txt").write_text(content, encoding="utf-8")


def main():
    """主函数"""
    print("🚀 开始生成静态网站...")
    print(f"   输出目录: {OUTPUT_DIR}")

    # 清理输出目录
    if OUTPUT_DIR.exists():
        print("  清理旧文件...")
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # 导出数据
    data = export_complete_data()

    print(f"\n📊 数据统计:")
    print(f"   试卷: {len(data['papers'])} 套")
    print(f"   题目: {len(data['questions'])} 道")
    print(f"   知识点: {len(data['tags'])} 个")

    print(f"\n🎨 渲染页面...")

    # 渲染各个页面
    render_index(data, OUTPUT_DIR)
    render_papers(data, OUTPUT_DIR)
    render_paper_detail(data, OUTPUT_DIR)
    render_questions(data, OUTPUT_DIR)
    render_question_detail(data, OUTPUT_DIR)
    render_topics(data, OUTPUT_DIR)

    # 复制静态资源
    copy_static_files(OUTPUT_DIR)

    # 导出 JSON 数据
    export_json_data(data, OUTPUT_DIR)

    # 生成 SEO 文件
    generate_sitemap(OUTPUT_DIR)
    generate_robots_txt(OUTPUT_DIR)

    # 生成 404 页面
    print("  → 生成 404 页面...")
    (OUTPUT_DIR / "404.html").write_text("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>404 - 页面未找到</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/GaokaoMathBank/static/style-apple.css">
</head>
<body>
<div style="max-width: 600px; margin: 80px auto; text-align: center; padding: 20px;">
  <h1 style="font-size: 72px; color: #007AFF; margin: 0;">404</h1>
  <h2 style="color: #1D1D1F; margin: 20px 0;">页面未找到</h2>
  <p style="color: #86868B; margin: 20px 0;">您访问的页面不存在或已被移除</p>
  <a href="/GaokaoMathBank/" style="display: inline-block; margin-top: 20px; padding: 12px 24px; background: #007AFF; color: white; border-radius: 12px; text-decoration: none; font-weight: 500;">返回首页</a>
</div>
</body>
</html>
""", encoding="utf-8")

    print(f"\n✅ 静态网站生成完成！")
    print(f"   输出目录: {OUTPUT_DIR}")
    print(f"   总文件数: {sum(1 for _ in OUTPUT_DIR.rglob('*') if _.is_file())}")
    print(f"   总大小: {sum(_.stat().st_size for _ in OUTPUT_DIR.rglob('*') if _.is_file()) / 1024 / 1024:.1f} MB")

    print(f"\n📤 下一步:")
    print(f"   1. 将代码推送到 GitHub")
    print(f"   2. 在仓库设置中启用 GitHub Pages")
    print(f"   3. 选择 'Deploy from branch' → 'docs' 分支")
    print(f"   4. 访问: https://tsing-cv.github.io/GaokaoMathBank/")


if __name__ == "__main__":
    main()
