#!/bin/bash
# 高考数学题库 - 公网访问启动脚本
# 使用方法: ./start-public.sh

echo "🚀 高考数学题库 - 公网启动中..."
echo "================================"
echo

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在正确目录
cd "$(dirname "$0")"

# 检查 Python 环境
if [ ! -d "/Users/mac/anaconda3/envs/aienv" ]; then
    echo -e "${YELLOW}⚠️  未找到 aienv 环境，尝试使用系统 Python...${NC}"
    PYTHON=python3
else
    PYTHON="/Users/mac/anaconda3/envs/aienv/bin/python"
fi

# 检查依赖
if ! $PYTHON -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}📦 安装依赖...${NC}"
    $PYTHON -m pip install -q -r requirements.txt
fi

# 清理函数
cleanup() {
    echo
    echo -e "${YELLOW}🛑 正在关闭服务...${NC}"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
    fi
    if [ ! -z "$TUNNEL_PID" ]; then
        kill $TUNNEL_PID 2>/dev/null
    fi
    echo -e "${GREEN}✅ 服务已停止${NC}"
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 启动 FastAPI 服务器
echo -e "${BLUE}📡 启动本地服务器...${NC}"
$PYTHON -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning &
SERVER_PID=$!

# 等待服务器启动
sleep 3

# 检查服务器是否成功启动
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${YELLOW}❌ 服务器启动失败${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 本地服务器已启动 (http://127.0.0.1:8000)${NC}"
echo

# 启动 localtunnel
echo -e "${BLUE}🌐 创建公网隧道...${NC}"
echo -e "${YELLOW}⏳ 请稍候(约 10-20 秒)...${NC}"
echo

# 使用 localtunnel 创建隧道
lt --port 8000 --subdomain gaokao-math &> /tmp/lt-output.txt &
TUNNEL_PID=$!

# 等待隧道建立并获取 URL
sleep 8

# 读取隧道 URL
if [ -f /tmp/lt-output.txt ]; then
    TUNNEL_URL=$(grep -o 'https://[^ ]*' /tmp/lt-output.txt | head -1)
fi

# 如果没获取到 URL，尝试其他方式
if [ -z "$TUNNEL_URL" ]; then
    sleep 5
    TUNNEL_URL=$(grep -o 'https://[^ ]*' /tmp/lt-output.txt 2>/dev/null | head -1)
fi

echo
echo "================================"
echo -e "${GREEN}🎉 部署成功！${NC}"
echo "================================"
echo
if [ ! -z "$TUNNEL_URL" ]; then
    echo -e "${BLUE}🌍 公网访问地址:${NC}"
    echo -e "${GREEN}$TUNNEL_URL${NC}"
    echo
    echo -e "${YELLOW}📱 将此链接分享给任何人即可访问${NC}"
else
    echo -e "${YELLOW}⚠️  隧道建立中，请稍等...${NC}"
    echo -e "查看隧道状态: cat /tmp/lt-output.txt"
    echo -e "或手动运行: lt --port 8000"
fi
echo
echo "================================"
echo -e "本地访问: ${GREEN}http://127.0.0.1:8000${NC}"
echo -e "按 ${YELLOW}Ctrl+C${NC} 停止服务"
echo "================================"
echo

# 隧道断线自动重连(每 5 分钟检测一次)
echo -e "${BLUE}🔄 已启用隧道自动保活(每 5 分钟检测)${NC}"
echo

while true; do
    sleep 300  # 每 5 分钟检测一次
    if ! curl -s -o /dev/null -f --connect-timeout 5 "https://gaokao-math.loca.lt" 2>/dev/null; then
        echo -e "$(date '+%H:%M:%S') ${YELLOW}⚠️  隧道断开，正在重连...${NC}"
        pkill -f "lt --port 8000" 2>/dev/null
        sleep 2
        lt --port 8000 --subdomain gaokao-math &> /tmp/lt-output.txt &
        TUNNEL_PID=$!
        sleep 5
        echo -e "$(date '+%H:%M:%S') ${GREEN}✅ 隧道已重连${NC}"
    else
        echo -e "$(date '+%H:%M:%S') ${GREEN}✅ 隧道正常${NC}"
    fi
done
