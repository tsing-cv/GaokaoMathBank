#!/bin/bash
# 高考数学题库 - GitHub Pages 快速部署脚本

set -e  # 遇到错误立即退出

echo "🚀 高考数学题库 - GitHub Pages 部署脚本"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 步骤 1: 检查依赖
echo -e "${BLUE}📦 步骤 1/6: 检查依赖...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 依赖检查通过${NC}"
echo ""

# 步骤 2: 检查数据库
echo -e "${BLUE}🔍 步骤 2/6: 检查数据库...${NC}"
if [ ! -f "data/mathbank.db" ]; then
    echo -e "${RED}❌ 数据库文件不存在: data/mathbank.db${NC}"
    echo "请先运行数据采集脚本"
    exit 1
fi

echo -e "${GREEN}✅ 数据库文件存在 ($(du -h data/mathbank.db | cut -f1))${NC}"
echo ""

# 步骤 3: 安装 Python 依赖
echo -e "${BLUE}📦 步骤 3/6: 安装 Python 依赖...${NC}"
if [ -f "requirements.txt" ]; then
    pip3 install -q -r requirements.txt
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt 不存在，跳过依赖安装${NC}"
fi
echo ""

# 步骤 4: 生成静态网站
echo -e "${BLUE}🏗️  步骤 4/6: 生成静态网站...${NC}"
python3 scripts/render_static.py
echo ""

# 步骤 5: 验证生成结果
echo -e "${BLUE}✅ 步骤 5/6: 验证生成结果...${NC}"
if [ ! -d "docs" ]; then
    echo -e "${RED}❌ docs 目录不存在${NC}"
    exit 1
fi

if [ ! -f "docs/index.html" ]; then
    echo -e "${RED}❌ docs/index.html 不存在${NC}"
    exit 1
fi

FILE_COUNT=$(find docs -type f | wc -l)
TOTAL_SIZE=$(du -sh docs | cut -f1)

echo -e "${GREEN}✅ 静态网站生成成功${NC}"
echo "   文件数: ${FILE_COUNT}"
echo "   总大小: ${TOTAL_SIZE}"
echo ""

# 步骤 6: Git 操作
echo -e "${BLUE}📤 步骤 6/6: Git 操作...${NC}"

# 检查是否在 git 仓库中
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    echo -e "${YELLOW}⚠️  当前目录不是 Git 仓库${NC}"
    echo "请手动执行以下命令："
    echo ""
    echo "  git init"
    echo "  git add docs/"
    echo "  git commit -m '📝 生成静态网站'"
    echo "  git remote add origin https://github.com/tsing-cv/GaokaoMathBank.git"
    echo "  git push -u origin main"
    echo ""
    exit 0
fi

# 检查是否有更改
if git diff --quiet docs/; then
    echo -e "${YELLOW}⚠️  docs 目录没有更改，跳过提交${NC}"
else
    echo "添加 docs 目录到 Git..."
    git add docs/
    git add -A

    echo "提交更改..."
    git commit -m "📝 更新静态网站

- 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
- 文件数: ${FILE_COUNT}
- 总大小: ${TOTAL_SIZE}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Code <noreply@anthropic.com>"

    echo "推送到 GitHub..."
    git push origin main

    echo -e "${GREEN}✅ 代码已推送到 GitHub${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo "📋 下一步操作："
echo ""
echo "1️⃣  配置 GitHub Pages:"
echo "   https://github.com/tsing-cv/GaokaoMathBank/settings/pages"
echo ""
echo "   - Source: Deploy from a branch"
echo "   - Branch: main"
echo "   - Folder: /docs"
echo "   - 点击 Save"
echo ""
echo "2️⃣  等待 1-2 分钟部署完成"
echo ""
echo "3️⃣  访问您的网站:"
echo "   ${BLUE}https://tsing-cv.github.io/GaokaoMathBank/${NC}"
echo ""
echo "📊 网站统计:"
echo "   - 文件数: ${FILE_COUNT}"
echo "   - 总大小: ${TOTAL_SIZE}"
echo "   - 试卷: 811 套"
echo "   - 题目: 15,608 道"
echo "   - 知识点: 15 个"
echo ""
echo "💡 提示:"
echo "   - 查看构建进度: https://github.com/tsing-cv/GaokaoMathBank/actions"
echo "   - 详细文档: cat GITHUB_PAGES_DEPLOY.md"
echo ""
echo "========================================"
