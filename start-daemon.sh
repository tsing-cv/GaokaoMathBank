#!/bin/bash
# 高考数学题库 - 永久运行版(开机自启 + 自动保活)

cd "$(dirname "$0")"

PYTHON="/Users/mac/anaconda3/envs/aienv/bin/python"
LOG="$HOME/Library/Logs/gaokao-math.log"

# 确保目录存在
mkdir -p "$HOME/Library/Logs"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG"
}

log "=== 服务启动 ==="

# 启动 FastAPI 服务器
$PYTHON -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level error >> "$LOG" 2>&1 &
SERVER_PID=$!
log "服务器 PID: $SERVER_PID"

sleep 3

# 启动隧道 + 保活循环
while true; do
    # 检查本地服务器
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        log "️  服务器已停止，重启中..."
        $PYTHON -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level error >> "$LOG" 2>&1 &
        SERVER_PID=$!
        sleep 3
    fi

    # 检查隧道
    if ! curl -s -o /dev/null -f --connect-timeout 5 "https://gaokao-math.loca.lt" 2>/dev/null; then
        log "⚠️  隧道断开，重连中..."
        pkill -f "lt --port 8000" 2>/dev/null
        sleep 2
        lt --port 8000 --subdomain gaokao-math >> "$LOG" 2>&1 &
        sleep 8

        if curl -s -o /dev/null -f --connect-timeout 5 "https://gaokao-math.loca.lt" 2>/dev/null; then
            log "✅ 隧道已恢复"
        else
            log "❌ 重连失败，1 分钟后重试"
        fi
    fi

    # 每 60 秒检测一次
    sleep 60
done
