# 🚀 GitHub Pages 部署指南

## 📋 概述

本指南将帮助您将高考数学题库部署到 GitHub Pages，让公网可以访问。

**最终访问地址：** https://tsing-cv.github.io/GaokaoMathBank/

---

## 🎯 部署方案

### 技术方案

- **静态网站生成器** - 将 FastAPI 动态网站预渲染为静态 HTML
- **GitHub Pages** - 免费托管静态网站
- **GitHub Actions** - 自动构建和部署

### 架构

```
源代码 (main 分支)
  ↓
GitHub Actions (自动构建)
  ↓
静态网站 (docs 目录)
  ↓
GitHub Pages (公网访问)
```

---

## 📦 前置要求

### 1. GitHub 仓库

确保您的代码已推送到 GitHub：
```
https://github.com/tsing-cv/GaokaoMathBank
```

### 2. 数据库文件

确保 `data/mathbank.db` 存在且包含数据：
```bash
ls -lh data/mathbank.db
# 应该显示类似: -rw-r--r--  1 user  staff   145M Oct 19 01:00 data/mathbank.db
```

### 3. Python 依赖

安装必要的 Python 包：
```bash
pip install -r requirements.txt
```

需要的包：
- `fastapi` - Web 框架
- `jinja2` - 模板引擎
- `sqlalchemy` - 数据库 ORM
- `httpx` - HTTP 客户端

---

## 🚀 部署步骤

### 步骤 1: 本地测试静态网站生成

在本地生成静态网站并测试：

```bash
# 1. 生成静态网站
python scripts/render_static.py

# 2. 查看生成的文件
ls -lh docs/

# 3. 本地预览（使用 Python 内置服务器）
cd docs
python -m http.server 8080

# 4. 访问 http://localhost:8080 查看效果
```

### 步骤 2: 提交代码到 GitHub

```bash
# 添加所有更改
git add .

# 提交
git commit -m "✨ 添加 GitHub Pages 静态网站支持

- 创建静态网站生成器 scripts/render_static.py
- 添加 GitHub Actions 自动部署工作流
- 生成静态 HTML 页面到 docs 目录
- 导出 JSON 数据供客户端使用

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Code <noreply@anthropic.com>"

# 推送到 GitHub
git push origin main
```

### 步骤 3: 配置 GitHub Pages

1. **访问仓库设置**
   ```
   https://github.com/tsing-cv/GaokaoMathBank/settings
   ```

2. **启用 GitHub Pages**
   - 点击左侧菜单的 **Pages**
   - **Source** 选择: **Deploy from a branch**
   - **Branch** 选择: **main**
   - **Folder** 选择: **/docs**
   - 点击 **Save**

3. **等待部署完成**
   - 首次部署需要 1-2 分钟
   - 可以在 **Actions** 标签页查看构建进度

### 步骤 4: 访问您的网站

部署完成后，访问：
```
https://tsing-cv.github.io/GaokaoMathBank/
```

---

## 🔄 自动部署

### 触发条件

GitHub Actions 会在以下情况自动构建和部署：

1. **推送到 main 分支** - 每次代码更新
2. **手动触发** - 在 Actions 页面点击 "Run workflow"
3. **定时构建** - 每周日 UTC 00:00 自动重建

### 查看构建状态

```
https://github.com/tsing-cv/GaokaoMathBank/actions
```

### 手动触发构建

1. 访问 Actions 页面
2. 选择 **"Build and Deploy Static Site to GitHub Pages"**
3. 点击 **"Run workflow"**
4. 选择分支，点击 **"Run workflow"**

---

## 📊 生成的文件结构

```
docs/
├── index.html              # 首页
├── 404.html                # 404 页面
├── sitemap.xml             # 站点地图
├── robots.txt              # 搜索引擎爬虫配置
│
├── papers/                 # 试卷库
│   └── index.html
│
├── paper/                  # 试卷详情页
│   ├── 1.html
│   ├── 2.html
│   └── ... (886 个文件)
│
├── questions/              # 题库检索
│   └── index.html
│
├── question/               # 题目详情页
│   ├── 1.html
│   ├── 2.html
│   └── ... (15,608 个文件)
│
├── topics/                 # 知识点专题
│   └── index.html
│
├── static/                 # 静态资源
│   ├── style-apple.css    # 苹果风格样式
│   └── search.js          # 搜索功能
│
├── data/                   # JSON 数据
│   ├── papers.json        # 试卷列表
│   ├── questions.json     # 题目数据
│   ├── tags.json          # 知识点统计
│   ├── stats.json         # 统计信息
│   └── filters.json       # 筛选选项
│
└── assets/                 # 图片资源
    └── ... (题目图片)
```

---

## 🎨 自定义配置

### 修改网站标题

编辑 `app/templates/base.html`:
```html
<a class="brand" href="/">
  <span class="logo">∑</span>
  高考数学题库  <!-- 修改这里 -->
</a>
```

### 修改主题颜色

编辑 `app/static/style-apple.css`:
```css
:root {
  /* Apple Blue */
  --apple-blue: #007AFF;  /* 修改主色调 */
  --apple-blue-hover: #0051D5;
  --apple-blue-active: #0047BA;
}
```

### 添加 Google Analytics

编辑 `app/templates/base.html`，在 `</head>` 前添加：
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

---

## 🐛 故障排查

### 问题 1: GitHub Pages 显示 404

**原因:** docs 目录不存在或未正确配置

**解决:**
```bash
# 1. 检查 docs 目录是否存在
ls -la docs/

# 2. 如果不存在，手动生成
python scripts/render_static.py

# 3. 提交并推送
git add docs/
git commit -m "📝 生成静态网站"
git push
```

### 问题 2: 样式不加载

**原因:** 静态资源路径错误

**解决:**
```bash
# 检查 static 目录是否存在
ls -la docs/static/

# 如果不存在，手动复制
cp -r app/static/* docs/static/
git add docs/static/
git commit -m "🎨 修复静态资源路径"
git push
```

### 问题 3: 数据库文件过大

**原因:** GitHub 单文件限制 100MB

**解决:**
```bash
# 使用 Git LFS 管理大文件
git lfs install
git lfs track "data/mathbank.db"
git add .gitattributes
git commit -m "📦 使用 Git LFS 管理数据库"
git push
```

### 问题 4: 构建失败

**查看构建日志:**
```
https://github.com/tsing-cv/GaokaoMathBank/actions
```

**常见错误:**
- Python 依赖缺失 - 检查 `requirements.txt`
- 数据库文件不存在 - 确认 `data/mathbank.db` 已提交
- 模板语法错误 - 检查 Jinja2 模板

---

## 📈 性能优化

### 1. 启用 CDN 缓存

GitHub Pages 自动启用 CDN，但您可以添加缓存头：

创建 `docs/_headers` 文件：
```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

/static/*
  Cache-Control: public, max-age=31536000

/data/*
  Cache-Control: public, max-age=3600
```

### 2. 压缩资源

使用在线工具压缩 CSS/JS：
- CSS: https://cssnano.co/
- JS: https://terser.org/

### 3. 图片优化

使用 WebP 格式：
```bash
# 批量转换图片
find docs/assets -name "*.png" -exec convert {} {}.webp \;
```

### 4. 预加载关键资源

在 `base.html` 的 `<head>` 中添加：
```html
<link rel="preload" href="/GaokaoMathBank/static/style-apple.css" as="style">
<link rel="preload" href="/GaokaoMathBank/data/questions.json" as="fetch" crossorigin>
```

---

## 🔍 SEO 优化

### 1. 站点地图

已自动生成 `sitemap.xml`，包含所有页面。

提交到搜索引擎：
- Google: https://search.google.com/search-console
- Bing: https://www.bing.com/webmaster

### 2. Meta 标签

编辑 `app/templates/base.html`:
```html
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="高考数学真题库 - 2006-2026年全国卷及各省份高考数学真题，含详细解析">
  <meta name="keywords" content="高考数学,真题库,数学题,高考真题,解析">
  <meta name="author" content="Your Name">

  <!-- Open Graph -->
  <meta property="og:title" content="高考数学题库">
  <meta property="og:description" content="2006-2026年高考数学真题库">
  <meta property="og:image" content="https://tsing-cv.github.io/GaokaoMathBank/static/og-image.png">
  <meta property="og:url" content="https://tsing-cv.github.io/GaokaoMathBank/">
</head>
```

### 3. 结构化数据

添加 JSON-LD：
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "EducationalOrganization",
  "name": "高考数学题库",
  "description": "2006-2026年高考数学真题库",
  "url": "https://tsing-cv.github.io/GaokaoMathBank/"
}
</script>
```

---

## 📊 数据统计

### 查看网站统计

使用 Google Analytics 或其他统计工具：

1. 注册 Google Analytics
2. 获取跟踪 ID (GA_MEASUREMENT_ID)
3. 添加到 `base.html`（见上文）

### 监控构建状态

```
https://github.com/tsing-cv/GaokaoMathBank/actions
```

---

## 🔄 更新内容

### 添加新题目

1. 更新数据库 `data/mathbank.db`
2. 提交并推送：
   ```bash
   git add data/mathbank.db
   git commit -m "📝 添加新题目"
   git push
   ```
3. GitHub Actions 自动重建网站

### 修改样式

1. 编辑 `app/static/style-apple.css`
2. 提交并推送：
   ```bash
   git add app/static/style-apple.css
   git commit -m "🎨 更新样式"
   git push
   ```
3. GitHub Actions 自动重建网站

---

## 💡 最佳实践

### 1. 使用分支

- `main` - 生产环境（自动部署）
- `dev` - 开发环境（测试新功能）

### 2. 定期备份

```bash
# 备份数据库
cp data/mathbank.db data/mathbank.db.backup

# 提交备份
git add data/mathbank.db.backup
git commit -m "💾 备份数据库"
```

### 3. 版本控制

使用语义化版本：
```bash
git tag -a v1.0.0 -m "🎉 第一个稳定版本"
git push origin v1.0.0
```

### 4. 文档维护

保持 README.md 和文档更新：
```bash
git add README.md
git commit -m "📝 更新文档"
```

---

## 📞 获取帮助

### 官方文档

- GitHub Pages: https://pages.github.com/
- GitHub Actions: https://docs.github.com/cn/actions

### 社区支持

- GitHub Community: https://github.community/
- Stack Overflow: https://stackoverflow.com/questions/tagged/github-pages

### 问题反馈

如有问题，请提交 Issue：
```
https://github.com/tsing-cv/GaokaoMathBank/issues
```

---

## ✅ 检查清单

部署前请确认：

- [ ] 数据库文件 `data/mathbank.db` 存在
- [ ] Python 依赖已安装
- [ ] 本地测试静态网站生成成功
- [ ] 代码已推送到 GitHub
- [ ] GitHub Pages 已启用并配置
- [ ] 网站可以正常访问

---

## 🎉 完成！

恭喜！您的高考数学题库已成功部署到 GitHub Pages。

**访问地址：** https://tsing-cv.github.io/GaokaoMathBank/

**主要页面：**
- 首页: https://tsing-cv.github.io/GaokaoMathBank/
- 试卷库: https://tsing-cv.github.io/GaokaoMathBank/papers/
- 题库检索: https://tsing-cv.github.io/GaokaoMathBank/questions/
- 知识点专题: https://tsing-cv.github.io/GaokaoMathBank/topics/

---

**最后更新:** 2026-10-19  
**维护者:** Your Team  
**许可证:** MIT
