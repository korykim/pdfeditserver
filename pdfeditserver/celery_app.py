#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Celery应用配置

这个模块配置Celery应用实例，用于处理PDF编辑任务队列。
"""

import os
import redis
from celery import Celery
import dotenv
import json

# 加载环境变量
dotenv.load_dotenv()

# 获取Celery配置
broker_url = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
result_backend = os.environ.get('CELERY_RESULT_BACKEND', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))

# 创建Redis连接
redis_client = redis.from_url(broker_url)

# 创建任务存储类
class RedisTaskStore:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.prefix = 'pdf_task:'
        print("初始化 RedisTaskStore")
        
    def __getitem__(self, task_id):
        key = f"{self.prefix}{task_id}"
        data = self.redis.get(key)
        if data is None:
            print(f"Redis中找不到任务: {key}")
            raise KeyError(task_id)
        result = json.loads(data)
        print(f"从Redis获取任务 {key}: {result}")
        return result
        
    def __setitem__(self, task_id, value):
        key = f"{self.prefix}{task_id}"
        print(f"更新Redis任务 {key}: {value}")
        self.redis.set(key, json.dumps(value))
        
    def __delitem__(self, task_id):
        key = f"{self.prefix}{task_id}"
        print(f"删除Redis任务: {key}")
        self.redis.delete(key)
        
    def __contains__(self, task_id):
        key = f"{self.prefix}{task_id}"
        exists = self.redis.exists(key)
        print(f"检查Redis任务是否存在 {key}: {exists}")
        return exists
        
    def update(self, task_id, value):
        """更新任务状态，合并现有数据和新数据"""
        key = f"{self.prefix}{task_id}"
        try:
            # 获取现有数据
            current_data = self[task_id]
            # 合并数据
            current_data.update(value)
            # 保存更新后的数据
            print(f"更新Redis任务 {key}，合并后的数据: {current_data}")
            self[task_id] = current_data
            return current_data
        except Exception as e:
            print(f"更新Redis任务时出错 {key}: {str(e)}")
            raise
            
    def clear(self):
        """清除所有任务"""
        try:
            # 获取所有任务的键
            pattern = f"{self.prefix}*"
            keys = self.redis.keys(pattern)
            print(f"正在清除所有任务，找到 {len(keys)} 个任务")
            
            if keys:
                # 删除所有任务
                self.redis.delete(*keys)
                print(f"已清除 {len(keys)} 个任务")
            return len(keys)
        except Exception as e:
            print(f"清除任务时出错: {str(e)}")
            raise
            
    def items(self):
        """获取所有任务的迭代器"""
        try:
            # 获取所有任务的键
            pattern = f"{self.prefix}*"
            keys = self.redis.keys(pattern)
            
            # 遍历所有键，返回(task_id, task_data)对
            for key in keys:
                task_id = key.decode('utf-8').replace(self.prefix, '')
                try:
                    task_data = self[task_id]
                    yield task_id, task_data
                except Exception as e:
                    print(f"获取任务数据时出错 {key}: {str(e)}")
                    continue
        except Exception as e:
            print(f"获取任务列表时出错: {str(e)}")
            raise

# 创建全局任务存储实例
task_store = RedisTaskStore(redis_client)

# 创建Celery应用
celery_app = Celery(
    'pdfeditserver',
    broker=broker_url,
    backend=result_backend,
    include=['pdfeditserver.tasks']
)

# Celery配置
celery_app.conf.update(
    result_expires=3600,  # 结果过期时间（秒）
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=False,
    worker_max_tasks_per_child=100,  # 每个worker处理的最大任务数
    task_acks_late=True,  # 任务完成后再确认
    task_reject_on_worker_lost=True,  # worker丢失时拒绝任务
    task_track_started=True,  # 跟踪任务开始状态
    broker_connection_retry=True,  # 连接代理失败时重试
    broker_connection_retry_on_startup=True,  # 启动时连接代理失败时重试
    broker_connection_max_retries=10,  # 最大重试次数
    worker_prefetch_multiplier=4,  # worker预取任务数量
    worker_concurrency=os.cpu_count() or 4,  # worker并发数
)

if __name__ == '__main__':
    celery_app.start() 