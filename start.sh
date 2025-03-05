#!/bin/bash

# 启动脚本 - 启动PDF编辑服务器的所有组件

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖是否安装
echo "检查依赖..."
if ! python3 -c "import flask, celery, redis, PyPDF2" &> /dev/null; then
    echo "安装依赖..."
    pip install -r requirements.txt
fi

# 检查Redis是否运行
echo "检查Redis服务..."
if ! redis-cli ping &> /dev/null; then
    echo "警告: Redis服务未运行，任务队列将无法工作"
    echo "请使用以下命令启动Redis:"
    echo "  docker run -d -p 6379:6379 redis"
    echo "或者"
    echo "  redis-server"
    read -p "是否继续启动应用? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 创建日志目录
mkdir -p logs

# 启动Celery Worker
echo "启动Celery Worker..."
celery -A pdfeditserver.celery_app worker --loglevel=info > logs/worker.log 2>&1 &
WORKER_PID=$!
echo "Celery Worker 已启动 (PID: $WORKER_PID)"

# 启动Celery Beat
echo "启动Celery Beat..."
celery -A pdfeditserver.celery_app beat --loglevel=info > logs/beat.log 2>&1 &
BEAT_PID=$!
echo "Celery Beat 已启动 (PID: $BEAT_PID)"

# 启动Flask应用
echo "启动Flask应用..."
python -m pdfeditserver.app > logs/app.log 2>&1 &
APP_PID=$!
echo "Flask应用已启动 (PID: $APP_PID)"

# 保存PID到文件
echo "$WORKER_PID $BEAT_PID $APP_PID" > .pid

echo "所有服务已启动!"
echo "访问 http://localhost:9000 使用PDF编辑服务"
echo "日志文件保存在 logs/ 目录"
echo "使用 ./stop.sh 停止所有服务" 