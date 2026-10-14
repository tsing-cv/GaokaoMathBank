#!/bin/bash
# 高考数学题库 - 快速部署到 Railway

set -e

echo "🚀 高考数学题库部署助手"
echo "======================"
echo

# 检查是否在正确目录
if [ ! -f "app/main.py" ]; then
    echo "❌ 请在 GaokaoMathBank 项目根目录运行此脚本"
    exit 1
fi

# 检查 Git 状态
if ! git diff --quiet HEAD; then
    echo "⚠️  检测到未提交的更改，建议先提交："
    echo "   git add . && git commit -m 'Ready for deployment'"
    echo
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ 项目目录检查通过"
echo

# 检查远程仓库
REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REMOTE" ]; then
    echo "📦 步骤 1: 创建 GitHub 仓库"
    echo "--------------------------------"
    echo "请在 GitHub 上创建新仓库："
    echo "1. 访问 https://github.com/new"
    echo "2. 仓库名: gaokaomathbank"
    echo "3. 设为 Private(推荐)"
    echo "4. 不要初始化 README/gitignore"
    echo
    read -p "创建完成后，粘贴仓库地址: " REPO_URL
    git remote add origin "$REPO_URL"
    echo "✅ 远程仓库已添加: $REPO_URL"
else
    echo "✅ 远程仓库已配置: $REMOTE"
fi

echo
echo "📤 步骤 2: 推送代码到 GitHub"
echo "--------------------------------"
git push -u origin main 2>/dev/null || git push -u origin master
echo "✅ 代码已推送"

echo
echo "🌐 步骤 3: 部署到 Railway"
echo "--------------------------------"
echo "请选择部署方式："
echo "1) 通过网页部署(推荐，更直观)"
echo "2) 通过 Railway CLI(需要安装)"
echo
read -p "请选择 (1/2): " DEPLOY_METHOD

if [ "$DEPLOY_METHOD" == "1" ]; then
    echo
    echo "📱 网页部署步骤："
    echo "1. 访问 https://railway.app"
    echo "2. 使用 GitHub 登录"
    echo "3. 点击 'New Project' → 'Deploy from GitHub repo'"
    echo "4. 选择你的 gaokaomathbank 仓库"
    echo "5. Railway 会自动检测 Dockerfile 并开始构建"
    echo "6. 等待构建完成(约 5-10 分钟)"
    echo
    echo "⚙️  配置持久化存储："
    echo "1. 在 Railway 面板点击你的服务"
    echo "2. 进入 'Settings' → 'Volumes'"
    echo "3. 点击 'Add Volume'"
    echo "4. 挂载路径: /app/data"
    echo "5. 保存后服务会自动重启"
    echo
    echo "🔗 生成访问地址："
    echo "1. 进入 'Settings' → 'Networking'"
    echo "2. 点击 'Generate Domain'"
    echo "3. 复制生成的 URL(如: https://xxx.up.railway.app)"
elif [ "$DEPLOY_METHOD" == "2" ]; then
    echo
    if ! command -v railway &> /dev/null; then
        echo "📦 安装 Railway CLI..."
        npm install -g @railway/cli
    fi

    echo "🔐 登录 Railway..."
    railway login

    echo "🚀 初始化并部署..."
    railway init
    railway up

    echo
    echo "📁 配置持久化存储..."
    echo "请在 Railway 面板手动添加 Volume:"
    echo "路径: /app/data"
    echo
    echo "🔗 生成域名..."
    echo "请在 Railway 面板:"
    echo "Settings → Networking → Generate Domain"
else
    echo "❌ 无效选择"
    exit 1
fi

echo
echo "📊 步骤 4: 上传数据库"
echo "--------------------------------"
echo "数据库文件: data/mathbank.db (138MB)"
echo
echo "上传方式(三选一)："
echo
echo "方式 A: Railway CLI(推荐)"
echo "  railway volume upload data/mathbank.db --path /app/data/mathbank.db"
echo
echo "方式 B: 重新采集(首次部署)"
echo "  railway run python tools/run_collect.py --source github-gaokao-latex"
echo "  railway run python tools/run_collect.py --source github-gaokaomath"
echo
echo "方式 C: 手动上传到 Railway 面板"
echo "  Settings → Volumes → 你的卷 → Upload"

echo
echo "✅ 部署完成！"
echo "--------------------------------"
echo "请访问你的 Railway URL 测试访问"
echo "如有问题，查看 DEPLOYMENT.md 故障排查章节"
echo
