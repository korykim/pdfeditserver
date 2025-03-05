#!/bin/bash

# 停止脚本 - 停止PDF编辑服务器的所有组件

# 检查PID文件是否存在
if [ ! -f .pid ]; then
    echo "未找到PID文件，服务可能未运行"
    exit 1
fi

# 读取PID
read WORKER_PID BEAT_PID APP_PID < .pid

# 停止Flask应用
if ps -p $APP_PID > /dev/null; then
    echo "停止Flask应用 (PID: $APP_PID)..."
    kill $APP_PID
    sleep 1
    if ps -p $APP_PID > /dev/null; then
        echo "Flask应用未能正常停止，强制终止..."
        kill -9 $APP_PID
    fi
else
    echo "Flask应用未运行"
fi

# 停止Celery Beat
if ps -p $BEAT_PID > /dev/null; then
    echo "停止Celery Beat (PID: $BEAT_PID)..."
    kill $BEAT_PID
    sleep 1
    if ps -p $BEAT_PID > /dev/null; then
        echo "Celery Beat未能正常停止，强制终止..."
        kill -9 $BEAT_PID
    fi
else
    echo "Celery Beat未运行"
fi

# 停止Celery Worker
if ps -p $WORKER_PID > /dev/null; then
    echo "停止Celery Worker (PID: $WORKER_PID)..."
    kill $WORKER_PID
    sleep 2
    if ps -p $WORKER_PID > /dev/null; then
        echo "Celery Worker未能正常停止，强制终止..."
        kill -9 $WORKER_PID
    fi
else
    echo "Celery Worker未运行"
fi

# 删除PID文件
rm -f .pid

echo "所有服务已停止!" 